from flask import Blueprint, request, jsonify, g
from ..services import analysis_engine, ev_model, ai_service
from ..services.task_queue import create_analysis_task, get_task_status
from ..services.sector_rotation_service import get_sector_rotation_service
from ..services.capital_structure_service import get_capital_structure_service
from ..utils.auth import require_auth, get_user_id
from ..utils.decorators import check_quota, db_retry
from ..utils.serialization import convert_numpy_types
from ..models import db, ServiceType, StockAnalysisHistory, TaskType, TaskStatus, AnalysisTask, DailyAnalysisCache
from ..services.data_provider import DataProvider
from ..constants import detect_market_from_ticker
import logging
import json
from datetime import datetime, date
from sqlalchemy import func
import time
import threading
import requests

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stock')
logger = logging.getLogger(__name__)


def get_cached_analysis(ticker: str, style: str):
    """Returns cached analysis for today, or None."""
    today = date.today()
    return DailyAnalysisCache.query.filter_by(
        ticker=ticker, style=style, analysis_date=today
    ).first()


def get_in_progress_task_for_stock(ticker: str, style: str):
    """Returns an in-progress task for this ticker+style today, or None."""
    today = date.today()
    return AnalysisTask.query.filter(
        AnalysisTask.task_type == TaskType.STOCK_ANALYSIS.value,
        AnalysisTask.status.in_([TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]),
        AnalysisTask.input_params['ticker'].as_string() == ticker,
        AnalysisTask.input_params['style'].as_string() == style,
        func.date(AnalysisTask.created_at) == today
    ).first()
# --------------- Yahoo Finance Search helpers ---------------

class TTLCache:
    """Simple thread-safe dict cache with per-key TTL and max size."""

    def __init__(self, ttl: int = 300, max_size: int = 500):
        self._store: dict = {}  # key -> (value, expire_ts)
        self._lock = threading.Lock()
        self._ttl = ttl
        self._max_size = max_size

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expire_ts = entry
            if time.time() > expire_ts:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value):
        with self._lock:
            # Evict expired entries when approaching max size
            if len(self._store) >= self._max_size:
                now = time.time()
                expired = [k for k, (_, ts) in self._store.items() if now > ts]
                for k in expired:
                    del self._store[k]
                # If still too large, drop oldest entries
                if len(self._store) >= self._max_size:
                    oldest = sorted(self._store, key=lambda k: self._store[k][1])
                    for k in oldest[:len(self._store) - self._max_size + 1]:
                        del self._store[k]
            self._store[key] = (value, time.time() + self._ttl)


_search_cache = TTLCache(ttl=300, max_size=500)

EXCHANGE_TO_MARKET = {
    'NMS': 'US', 'NGM': 'US', 'NCM': 'US', 'NYQ': 'US', 'ASE': 'US',
    'PCX': 'US', 'BTS': 'US', 'OPR': 'US',
    'NASDAQ': 'US', 'NYSE': 'US', 'AMEX': 'US', 'NYSEARCA': 'US',
    'NYSEAMERICAN': 'US',
    'HKG': 'HK', 'HKSE': 'HK', 'HKS': 'HK',
    'SHH': 'CN', 'SHZ': 'CN', 'Shanghai': 'CN', 'Shenzhen': 'CN',
}


def _map_exchange_to_market(exchange: str, symbol: str) -> str:
    """Map Yahoo Finance exchange name to our market code (US/HK/CN)."""
    market = EXCHANGE_TO_MARKET.get(exchange)
    if market:
        return market
    # Fallback: infer from symbol suffix
    sym = symbol.upper()
    if sym.endswith('.HK'):
        return 'HK'
    if sym.endswith('.SS') or sym.endswith('.SZ'):
        return 'CN'
    return 'US'


def _normalize_search_queries(query: str) -> list:
    """
    Generate normalized search query variants for better matching.

    Handles:
    - HK stocks: 700, 0700, 00700 -> search for 700.HK
    - A-shares: 600519 -> search for 600519.SS
    - US stocks: AAPL -> search as-is

    Returns list of query variants to try.
    """
    query = query.strip().upper()
    variants = [query]  # Always try original

    # If it's purely numeric, handle market-specific formats
    if query.isdigit():
        stripped = query.lstrip('0') or '0'
        original_len = len(query)
        stripped_len = len(stripped)

        # HK stock patterns: 1-5 digit numbers (after stripping leading zeros)
        # User might input: 700, 0700, 00700 for Tencent (0700.HK)
        if stripped_len >= 1 and stripped_len <= 5:
            # Try HK format (Yahoo uses stripped version)
            hk_ticker = f"{stripped}.HK"
            if hk_ticker not in variants:
                variants.append(hk_ticker)
            # Also try padded HK format (some APIs expect 4-digit)
            hk_padded = f"{stripped.zfill(4)}.HK"
            if hk_padded not in variants:
                variants.append(hk_padded)

        # A-share patterns: 6 digits starting with 60/68/00/30
        if original_len == 6 or stripped_len == 6:
            code = query.zfill(6) if original_len < 6 else query
            prefix = code[:2]
            if prefix in ('60', '68'):
                ss_ticker = f"{code}.SS"
                if ss_ticker not in variants:
                    variants.append(ss_ticker)
            elif prefix in ('00', '30'):
                sz_ticker = f"{code}.SZ"
                if sz_ticker not in variants:
                    variants.append(sz_ticker)

        # Also try just the stripped number (Yahoo might handle it)
        if stripped != query and stripped not in variants:
            variants.append(stripped)

    # If query already has suffix, normalize HK format
    elif '.HK' in query:
        # Ensure we try both padded and stripped versions
        base = query.replace('.HK', '')
        if base.isdigit():
            stripped = base.lstrip('0') or '0'
            variants.append(f"{stripped}.HK")
            if stripped != base:
                variants.append(f"{base}.HK")

    return variants

@stock_bp.route('/search', methods=['GET'])
def search_stocks():
    """
    Fuzzy stock search via Yahoo Finance.
    GET /api/stock/search?q=QUERY&limit=8
    No auth required — must be fast for autocomplete.

    Supports multiple ticker formats:
    - US: AAPL, MSFT
    - HK: 700, 0700, 00700, 0700.HK (all find Tencent)
    - A-shares: 600519, 600519.SS
    """
    query = request.args.get('q', '').strip()
    limit = min(request.args.get('limit', 8, type=int), 20)

    if not query or len(query) < 1:
        return jsonify({'success': True, 'results': []})

    cache_key = f"{query.lower()}:{limit}"
    cached = _search_cache.get(cache_key)
    if cached is not None:
        return jsonify({'success': True, 'results': cached, 'source': 'cache'})

    # Generate search query variants for better matching
    search_variants = _normalize_search_queries(query)
    logger.debug(f"Search variants for '{query}': {search_variants}")

    try:
        ALLOWED_TYPES = {'EQUITY', 'ETF', 'FUND', 'MUTUALFUND'}
        seen_symbols = set()
        results = []

        # Try each variant until we have enough results
        for variant in search_variants:
            if len(results) >= limit:
                break

            try:
                resp = requests.get(
                    'https://query2.finance.yahoo.com/v1/finance/search',
                    params={
                        'q': variant,
                        'quotesCount': limit,
                        'newsCount': 0,
                        'listsCount': 0,
                        'enableFuzzyQuery': True,
                    },
                    headers={'User-Agent': 'Mozilla/5.0'},
                    timeout=4,
                )
                resp.raise_for_status()
                data = resp.json()

                for quote in data.get('quotes', []):
                    if len(results) >= limit:
                        break

                    qtype = quote.get('quoteType', '').upper()
                    if qtype not in ALLOWED_TYPES:
                        continue

                    symbol = quote.get('symbol', '')
                    # Deduplicate by normalized symbol
                    symbol_key = symbol.upper()
                    if symbol_key in seen_symbols:
                        continue
                    seen_symbols.add(symbol_key)

                    exchange = quote.get('exchange', '')
                    name_en = quote.get('shortname') or quote.get('longname') or ''
                    market = _map_exchange_to_market(exchange, symbol)
                    results.append({
                        'ticker': symbol,
                        'nameCn': '',
                        'nameEn': name_en,
                        'pinyin': '',
                        'market': market,
                    })

            except Exception as e:
                logger.debug(f"Yahoo search variant '{variant}' failed: {e}")
                continue

        _search_cache.set(cache_key, results)
        return jsonify({'success': True, 'results': results})

    except Exception as e:
        logger.warning(f"Yahoo Finance search failed for '{query}': {e}")
        return jsonify({'success': True, 'results': []})


def get_stock_analysis_data(ticker: str, style: str = 'quality', only_history: bool = False) -> dict:
    """
    Core stock analysis logic extracted for reuse in async tasks

    Args:
        ticker: Stock ticker symbol
        style: Analysis style (quality, value, growth, momentum)
        only_history: If True, return only historical data

    Returns:
        Analysis result dictionary or error dictionary
    """
    try:
        # 1. Get Market Data
        market_data = analysis_engine.get_market_data(ticker, onlyHistoryData=only_history)
        if not market_data or not market_data.get('price'):
            return {'error': f'找不到股票代码 "{ticker}" 或数据获取失败'}

        # If only requesting history data (e.g. for charts)
        if only_history:
            return market_data

        # 2. Risk Analysis (Matching original: analyze_risk_and_position)
        try:
            risk_result = analysis_engine.analyze_risk_and_position(style, market_data)
        except Exception as e:
            logger.error(f"计算风险评分时发生异常: {e}")
            return {'error': f'风险计算失败: {str(e)}'}

        # 3. Calculate Market Sentiment (Matching original)
        try:
            market_sentiment = analysis_engine.calculate_market_sentiment(market_data)
            market_data['market_sentiment'] = market_sentiment
        except Exception as e:
            logger.warning(f"计算市场情绪时发生异常: {e}")
            market_data['market_sentiment'] = 5.0  # Default value

        # 4. Calculate Target Price (Matching original)
        try:
            target_price = analysis_engine.calculate_target_price(market_data, risk_result, style)
            market_data['target_price'] = target_price
            
            # 根据目标价格和当前价格动态调整仓位
            current_price = market_data.get('price', 0)
            if current_price > 0 and target_price > 0:
                # 计算上涨空间百分比
                upside_pct = (target_price - current_price) / current_price
                
                # 根据上涨空间调整仓位
                # 如果目标价低于当前价，大幅降低仓位（不建议买入）
                if upside_pct < 0:
                    # 目标价低于当前价，仓位调整为0或极小值
                    price_adjustment = 0.0
                    risk_result['price_adjustment'] = price_adjustment
                    risk_result['suggested_position'] = 0.0
                    logger.info(f"目标价({target_price:.2f})低于当前价({current_price:.2f})，建议仓位调整为0%")
                elif upside_pct < 0.05:  # 上涨空间 < 5%
                    price_adjustment = 0.3  # 大幅降低仓位
                elif upside_pct < 0.10:  # 上涨空间 5-10%
                    price_adjustment = 0.6  # 适度降低仓位
                elif upside_pct < 0.20:  # 上涨空间 10-20%
                    price_adjustment = 0.9  # 轻微降低仓位
                elif upside_pct < 0.30:  # 上涨空间 20-30%
                    price_adjustment = 1.0  # 正常仓位
                else:  # 上涨空间 > 30%
                    price_adjustment = 1.1  # 可以适当增加仓位（但不超过基础上限）
                    price_adjustment = min(price_adjustment, 1.2)  # 最多增加20%
                
                # 应用价格调整
                base_position = risk_result.get('suggested_position', 0)
                adjusted_position = base_position * price_adjustment
                risk_result['price_adjustment'] = price_adjustment
                risk_result['suggested_position'] = round(adjusted_position, 1)
                risk_result['upside_potential_pct'] = round(upside_pct * 100, 2)
                
                logger.info(f"价格调整: 当前价={current_price:.2f}, 目标价={target_price:.2f}, 上涨空间={upside_pct:.2%}, 仓位调整系数={price_adjustment:.2f}, 最终仓位={adjusted_position:.1f}%")
        except Exception as e:
            logger.warning(f"计算目标价格时发生异常: {e}")
            market_data['target_price'] = market_data.get('price', 0)  # Default to current price

        # 4.5 Calculate Dynamic Stop Loss (Matching original - ATR based)
        try:
            # Get 1-month history for ATR calculation
            normalized_ticker = analysis_engine.normalize_ticker(ticker)
            stock = DataProvider(normalized_ticker)
            hist = stock.history(period="1mo", timeout=10)

            if not hist.empty and len(hist) >= 15:
                # 获取VIX值用于动态调整ATR倍数
                vix = None
                options_data = market_data.get('options_data', {})
                if options_data:
                    vix = options_data.get('vix')

                # Use ATR dynamic stop loss with VIX adjustment
                stop_loss_result = analysis_engine.calculate_atr_stop_loss(
                    buy_price=market_data['price'],
                    hist_data=hist,
                    atr_period=14,
                    atr_multiplier=2.5,
                    min_stop_loss_pct=0.05,
                    beta=market_data.get('beta'),
                    vix=vix
                )

                # 处理新的返回格式（dict）
                if isinstance(stop_loss_result, dict):
                    market_data['stop_loss_price'] = stop_loss_result['stop_loss_price']
                    market_data['stop_loss_method'] = 'ATR动态止损'
                    market_data['stop_loss_details'] = {
                        'atr_multiplier': stop_loss_result.get('atr_multiplier'),
                        'adjustments': stop_loss_result.get('adjustments', []),
                        'vix': stop_loss_result.get('vix'),
                        'beta': stop_loss_result.get('beta')
                    }
                else:
                    # 向后兼容：旧格式返回float
                    market_data['stop_loss_price'] = stop_loss_result
                    market_data['stop_loss_method'] = 'ATR动态止损'
            else:
                # Fallback to fixed stop loss
                stop_loss_price = market_data['price'] * 0.85
                market_data['stop_loss_price'] = stop_loss_price
                market_data['stop_loss_method'] = '固定15%止损（数据不足）'
        except Exception as e:
            logger.warning(f"计算止损价格时发生异常: {e}")
            # Fallback to fixed stop loss
            stop_loss_price = market_data.get('price', 0) * 0.85
            market_data['stop_loss_price'] = stop_loss_price
            market_data['stop_loss_method'] = '固定15%止损（计算失败）'

        # 4.6 板块轮动分析 (Sector Rotation Analysis)
        sector_analysis = None
        try:
            # 获取市场类型
            market = detect_market_from_ticker(ticker)
            sector = market_data.get('sector', 'Technology')
            industry = market_data.get('industry')

            sector_service = get_sector_rotation_service()
            sector_analysis = sector_service.analyze_stock_sector(
                ticker=ticker,
                sector=sector,
                industry=industry,
                stock_data=market_data,
                market=market
            )
            market_data['sector_analysis'] = sector_analysis
            logger.info(f"板块分析完成: {ticker}, 板块={sector_analysis.get('sector')}, 强度={sector_analysis.get('sector_strength')}, 溢价={sector_analysis.get('sector_rotation_premium', 0):.2%}")
        except Exception as e:
            logger.warning(f"板块分析时发生异常: {e}")
            sector_analysis = None
            market_data['sector_analysis'] = {
                'sector': market_data.get('sector', 'Unknown'),
                'alignment_score': 50,
                'is_sector_leader': False,
                'sector_rotation_premium': 0.0,
                'error': str(e)
            }

        # 4.7 资金结构分析 (Capital Structure Analysis)
        capital_analysis = None
        try:
            # 获取历史数据用于资金分析
            normalized_ticker = analysis_engine.normalize_ticker(ticker)
            capital_hist = DataProvider(normalized_ticker).history(period="3mo", timeout=10)

            capital_service = get_capital_structure_service()
            capital_analysis = capital_service.analyze_stock_capital(
                ticker=ticker,
                hist_data=capital_hist,
                market_data=market_data
            )
            market_data['capital_analysis'] = capital_analysis
            logger.info(f"资金分析完成: {ticker}, 集中度={capital_analysis.get('concentration_score')}, 阶段={capital_analysis.get('propagation_stage')}, 因子={capital_analysis.get('capital_factor', 0):.2%}")
        except Exception as e:
            logger.warning(f"资金分析时发生异常: {e}")
            capital_analysis = None
            market_data['capital_analysis'] = {
                'concentration_score': 50,
                'propagation_stage': 'neutral',
                'capital_factor': 0.0,
                'signals': [],
                'error': str(e)
            }

        # 4.8 Calculate EV Model (基础版本 + 扩展版本)
        try:
            # 基础EV模型
            ev_result = ev_model.calculate_ev_model(market_data, risk_result, style)

            # 扩展EV模型（整合板块和资金因子）
            ev_extended_result = ev_model.calculate_ev_model_extended(
                market_data, risk_result, style,
                sector_analysis=sector_analysis,
                capital_analysis=capital_analysis
            )

            # 合并结果，扩展版本包含基础版本所有字段
            market_data['ev_model'] = ev_extended_result
            logger.info(f"EV模型计算完成: {ticker}, 基础EV={ev_extended_result.get('ev_base_pct', 0):.2f}%, 扩展EV={ev_extended_result.get('ev_extended_pct', 0):.2f}%")
        except Exception as e:
            logger.warning(f"计算EV模型时发生异常: {e}")
            market_data['ev_model'] = {
                'error': str(e),
                'ev_weighted': 0.0,
                'ev_weighted_pct': 0.0,
                'ev_extended': 0.0,
                'ev_extended_pct': 0.0,
                'ev_score': 5.0,
                'recommendation': {
                    'action': 'HOLD',
                    'reason': 'EV模型计算失败',
                    'confidence': 'low'
                }
            }

        # 5. AI Analysis (Matching original - this takes time)
        try:
            ai_report = ai_service.get_gemini_analysis(ticker, style, market_data, risk_result)
        except Exception as e:
            logger.error(f"AI分析时发生异常: {e}")
            # Use fallback analysis
            ai_report = ai_service.get_fallback_analysis(ticker, style, market_data, risk_result)

        # 6. Construct Response (Matching original app.py format exactly)
        response = {
            'success': True,
            'data': market_data,
            'risk': risk_result,
            'report': ai_report
        }

        return response

    except Exception as e:
        logger.error(f"Error in stock analysis for {ticker}: {e}")
        return {'error': f'分析过程中发生错误: {str(e)}'}

@stock_bp.route('/analyze-async', methods=['POST'])
@require_auth
@check_quota(service_type=ServiceType.STOCK_ANALYSIS.value, amount=1)
def analyze_stock_async():
    """
    Create async stock analysis task (with daily cache support)

    Request Body:
    {
        "ticker": "AAPL",
        "style": "quality",  // optional, default quality
        "priority": 100      // optional, lower = higher priority
    }

    Returns:
    {
        "success": true,
        "task_id": "uuid-string",
        "message": "Analysis task created successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        ticker = data.get('ticker', '').upper()
        if not ticker:
            return jsonify({'success': False, 'error': 'Ticker is required'}), 400

        style = data.get('style', 'quality')
        priority = data.get('priority', 100)

        user_id = get_user_id()
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        # CASE A: Check if today's cache exists
        cache_entry = get_cached_analysis(ticker, style)
        if cache_entry:
            logger.info(f"[analyze-async] Cache HIT for {ticker}/{style}")
            task_id = create_analysis_task(
                user_id=user_id,
                task_type=TaskType.STOCK_ANALYSIS.value,
                input_params={'ticker': ticker, 'style': style},
                priority=priority,
                cache_mode='cached',
                cached_data=cache_entry.full_analysis_data
            )
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Analysis task created successfully'
            }), 201

        # CASE B: Check for in-progress task
        try:
            in_progress_task = get_in_progress_task_for_stock(ticker, style)
        except Exception:
            in_progress_task = None

        if in_progress_task:
            logger.info(f"[analyze-async] In-progress task found for {ticker}/{style}")
            task_id = create_analysis_task(
                user_id=user_id,
                task_type=TaskType.STOCK_ANALYSIS.value,
                input_params={'ticker': ticker, 'style': style},
                priority=priority,
                cache_mode='waiting',
                source_task_id=in_progress_task.id
            )
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Analysis task created successfully'
            }), 201

        # CASE C: No cache — run full analysis
        task_id = create_analysis_task(
            user_id=user_id,
            task_type=TaskType.STOCK_ANALYSIS.value,
            input_params={'ticker': ticker, 'style': style},
            priority=priority
        )

        logger.info(f"Created async stock analysis task {task_id} for {ticker} ({style}) - User: {user_id}")

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Analysis task created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error creating async stock analysis task: {e}")
        return jsonify({'success': False, 'error': f'Failed to create analysis task: {str(e)}'}), 500

@stock_bp.route('/analyze', methods=['POST'])
@check_quota(service_type=ServiceType.STOCK_ANALYSIS.value, amount=1)
def analyze_stock():
    """
    Stock Analysis Endpoint - Always uses async task queue with daily caching

    Accepts: {
        "ticker": "AAPL",
        "style": "quality",  # optional, default quality
        "onlyHistoryData": false, # optional, for chart data only (sync)
    }

    Returns:
    - onlyHistoryData=true: Sync JSON with chart data
    - Full analysis: {"success": true, "task_id": "uuid", "message": "..."}
      Always creates an async task. If today's cache exists, the task simulates
      progress over ~10s then returns cached data. Otherwise runs full analysis.
    """
    ticker = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        ticker = data.get('ticker', '').upper()
        if not ticker:
            return jsonify({'success': False, 'error': 'Ticker is required'}), 400

        style = data.get('style', 'quality')
        only_history = data.get('onlyHistoryData', False)

        user_id = getattr(g, 'user_id', None)
        logger.info(f"Analyzing stock {ticker} with style {style} for user {user_id}")

        # For chart-only data, keep sync mode (no yfinance heavy calls)
        if only_history:
            result = get_stock_analysis_data(ticker, style, only_history=True)
            if 'error' in result:
                return jsonify({'success': False, 'error': result['error']}), 400
            return jsonify({'success': True, 'data': result})

        # Full analysis — always use async task with cache logic
        if not user_id:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        # CASE A: Check if today's cache exists for this (ticker, style)
        cache_entry = get_cached_analysis(ticker, style)
        if cache_entry:
            logger.info(f"Cache HIT for {ticker}/{style} — creating fake-progress task")
            task_id = create_analysis_task(
                user_id=user_id,
                task_type=TaskType.STOCK_ANALYSIS.value,
                input_params={'ticker': ticker, 'style': style},
                priority=data.get('priority', 100),
                cache_mode='cached',
                cached_data=cache_entry.full_analysis_data
            )
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Analysis task created successfully'
            }), 201

        # CASE B: Check if another task for the same (ticker, style) is already in progress
        try:
            in_progress_task = get_in_progress_task_for_stock(ticker, style)
        except Exception as e:
            # JSON path query may not be supported on SQLite — fall through to CASE C
            logger.warning(f"In-progress task lookup failed (may not support JSON queries): {e}")
            in_progress_task = None

        if in_progress_task:
            logger.info(f"In-progress task found ({in_progress_task.id}) for {ticker}/{style} — creating waiting task")
            task_id = create_analysis_task(
                user_id=user_id,
                task_type=TaskType.STOCK_ANALYSIS.value,
                input_params={'ticker': ticker, 'style': style},
                priority=data.get('priority', 100),
                cache_mode='waiting',
                source_task_id=in_progress_task.id
            )
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Analysis task created successfully'
            }), 201

        # CASE C: No cache, no in-progress task — run full analysis
        logger.info(f"Cache MISS for {ticker}/{style} — creating real analysis task")
        task_id = create_analysis_task(
            user_id=user_id,
            task_type=TaskType.STOCK_ANALYSIS.value,
            input_params={'ticker': ticker, 'style': style},
            priority=data.get('priority', 100)
        )

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Analysis task created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Error analyzing stock {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'分析过程中发生错误: {str(e)}'}), 500


@stock_bp.route('/history', methods=['GET'])
@require_auth
@db_retry(max_retries=3, retry_delay=0.5)
def get_analysis_history():
    """
    Get user's stock analysis history
    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 10, max 50)
    - ticker: Filter by ticker (optional)
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)  # Max 50 per page
        ticker_filter = request.args.get('ticker', '').upper()

        query = StockAnalysisHistory.query.filter_by(user_id=g.user_id)

        if ticker_filter:
            query = query.filter(StockAnalysisHistory.ticker == ticker_filter)

        query = query.order_by(StockAnalysisHistory.created_at.desc())

        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        history_items = []
        for item in paginated.items:
            # Check if we have complete analysis data
            if item.full_analysis_data:
                # Support both old and new data formats
                if 'complete_response' in item.full_analysis_data:
                    # Old format: extract from complete_response wrapper
                    complete_analysis = item.full_analysis_data['complete_response'].copy()
                    logger.info(f"Using old format for history item {item.id}")
                else:
                    # New format: direct analysis data (no wrapper)
                    complete_analysis = item.full_analysis_data.copy()
                    logger.info(f"Using new format for history item {item.id}")

                # Add history metadata for list display
                complete_analysis['history_metadata'] = {
                    'id': item.id,
                    'created_at': item.created_at.isoformat(),
                    'is_from_history': True,
                    'ticker': item.ticker,
                    'style': item.style
                }

                history_items.append(complete_analysis)
            else:
                # Fallback for very old records without full_analysis_data
                logger.info(f"Using fallback format for history item {item.id}")
                history_items.append({
                    'success': True,
                    'data': {
                        'name': item.ticker,
                        'symbol': item.ticker,
                        'price': item.current_price,
                        'target_price': item.target_price,
                        'stop_loss_price': item.stop_loss_price,
                        'market_sentiment': item.market_sentiment
                    },
                    'risk': {
                        'score': item.risk_score,
                        'level': item.risk_level,
                        'suggested_position': item.position_size
                    },
                    'report': item.ai_summary or '历史分析数据',
                    'history_metadata': {
                        'id': item.id,
                        'created_at': item.created_at.isoformat(),
                        'is_from_history': True,
                        'ticker': item.ticker,
                        'style': item.style,
                        'incomplete_data': True
                    }
                })

        return jsonify({
            'success': True,
            'data': {
                'items': history_items,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated.total,
                    'pages': paginated.pages,
                    'has_next': paginated.has_next,
                    'has_prev': paginated.has_prev
                }
            }
        })

    except Exception as e:
        logger.error(f"Error fetching analysis history for user {g.user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@stock_bp.route('/history/<int:history_id>', methods=['GET'])
@require_auth
@db_retry(max_retries=3, retry_delay=0.5)
def get_analysis_history_detail(history_id):
    """
    Get detailed analysis history by ID including full analysis data
    """
    try:
        history_item = StockAnalysisHistory.query.filter_by(
            id=history_id,
            user_id=g.user_id
        ).first()

        if not history_item:
            return jsonify({'success': False, 'error': 'Analysis history not found'}), 404

        # Check if we have complete analysis data
        if history_item.full_analysis_data:
            # Support both old and new data formats
            if 'complete_response' in history_item.full_analysis_data:
                # Old format: extract from complete_response wrapper
                stored_response = history_item.full_analysis_data['complete_response'].copy()
                logger.info(f"Using old format for history detail {history_item.id}")
            else:
                # New format: direct analysis data (no wrapper)
                stored_response = history_item.full_analysis_data.copy()
                logger.info(f"Using new format for history detail {history_item.id}")

            # Add history metadata for frontend reference
            stored_response['history_metadata'] = {
                'id': history_item.id,
                'created_at': history_item.created_at.isoformat(),
                'is_from_history': True,
                'ticker': history_item.ticker,
                'style': history_item.style
            }

            logger.info(f"Returning complete stored analysis response for history ID {history_item.id}")
            return jsonify(stored_response)
        else:
            # Fallback for very old records without full_analysis_data
            logger.info(f"Using fallback format for history ID {history_item.id}")
            detail_response = {
                'success': True,
                'data': {
                    'name': history_item.ticker,
                    'symbol': history_item.ticker,
                    'price': history_item.current_price,
                    'target_price': history_item.target_price,
                    'stop_loss_price': history_item.stop_loss_price,
                    'market_sentiment': history_item.market_sentiment
                },
                'risk': {
                    'score': history_item.risk_score,
                    'level': history_item.risk_level,
                    'suggested_position': history_item.position_size
                },
                'report': history_item.ai_summary or '历史分析数据',
                'history_metadata': {
                    'id': history_item.id,
                    'created_at': history_item.created_at.isoformat(),
                    'is_from_history': True,
                    'ticker': history_item.ticker,
                    'style': history_item.style,
                    'incomplete_data': True
                }
            }
            return jsonify(detail_response)

    except Exception as e:
        logger.error(f"Error fetching analysis history detail {history_id} for user {g.user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@stock_bp.route('/test-history', methods=['POST'])
@require_auth
def test_history():
    """Test endpoint to verify history saving works"""
    try:
        logger.info(f"Testing history save for user: {g.user_id}")

        # Simple test record
        test_history = StockAnalysisHistory(
            user_id=g.user_id,
            ticker="TEST",
            style="test",
            current_price=100.0,
            target_price=110.0,
            stop_loss_price=95.0,
            market_sentiment=5.0,
            risk_score=3.0,
            risk_level="medium",
            position_size=10.0,
            ev_score=6.0,
            ev_weighted_pct=15.5,
            recommendation_action="buy",
            recommendation_confidence="high",
            ai_summary="Test AI summary",
            full_analysis_data={"test": "data"}
        )

        db.session.add(test_history)
        db.session.commit()

        logger.info(f"Successfully saved test history with ID: {test_history.id}")

        return jsonify({
            'success': True,
            'message': f'Test history saved with ID: {test_history.id}'
        })

    except Exception as e:
        logger.error(f"Failed to save test history: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@stock_bp.route('/summary/<ticker>', methods=['GET'])
@require_auth
def get_stock_summary(ticker):
    """
    获取股票分析摘要（用于期权页面联动）

    首次免费逻辑：
    - 如果用户从未分析过该股票，免费返回摘要
    - 如果用户已分析过该股票，返回历史数据（不消耗额度）
    - 如果需要重新分析，消耗额度

    Query Parameters:
    - force_refresh: 强制重新分析（消耗额度）

    Returns:
    {
        "success": true,
        "summary": {
            "ticker": "AAPL",
            "current_price": 185.50,
            "target_price": 195.00,
            "target_price_pct": "+5.1%",
            "stop_loss_price": 175.00,
            "market_sentiment": 7.5,
            "risk_score": 3.2,
            "risk_level": "medium",
            "position_size": 15.0,
            "ai_summary": "AAPL近期..."
        },
        "is_first_time": true,
        "from_history": false
    }
    """
    try:
        ticker = ticker.upper()
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'

        # 1. 检查历史记录（是否已分析过）
        existing_history = StockAnalysisHistory.query.filter_by(
            user_id=g.user_id,
            ticker=ticker
        ).order_by(StockAnalysisHistory.created_at.desc()).first()

        is_first_time = existing_history is None

        # 2. 如果有历史记录且不强制刷新，直接返回历史数据
        if existing_history and not force_refresh:
            logger.info(f"返回历史分析摘要: {ticker} (用户: {g.user_id})")

            summary = {
                'ticker': ticker,
                'current_price': existing_history.current_price,
                'target_price': existing_history.target_price,
                'target_price_pct': f"+{((existing_history.target_price - existing_history.current_price) / existing_history.current_price * 100):.1f}%" if existing_history.current_price and existing_history.target_price else None,
                'stop_loss_price': existing_history.stop_loss_price,
                'market_sentiment': existing_history.market_sentiment,
                'risk_score': existing_history.risk_score,
                'risk_level': existing_history.risk_level,
                'position_size': existing_history.position_size,
                'ev_score': existing_history.ev_score,
                'recommendation_action': existing_history.recommendation_action,
                'ai_summary': existing_history.ai_summary,
                'analyzed_at': existing_history.created_at.isoformat() if existing_history.created_at else None
            }

            return jsonify({
                'success': True,
                'summary': summary,
                'is_first_time': False,
                'from_history': True,
                'history_id': existing_history.id
            })

        # 3. 首次分析或强制刷新 - 执行分析
        # 首次免费，强制刷新需要额度
        if force_refresh and not is_first_time:
            # 检查额度
            from ..utils.decorators import check_and_deduct_quota
            quota_result = check_and_deduct_quota(g.user_id, ServiceType.STOCK_ANALYSIS.value, 1)
            if not quota_result.get('success'):
                return jsonify({
                    'success': False,
                    'error': '额度不足，无法重新分析',
                    'quota_error': True
                }), 403

        logger.info(f"执行股票分析摘要: {ticker} (用户: {g.user_id}, 首次: {is_first_time})")

        # 执行简化分析（只获取关键数据）
        result = get_stock_analysis_data(ticker, 'quality', only_history=False)

        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400

        # 提取摘要数据
        market_data = result.get('data', {})
        risk_result = result.get('risk', {})
        ev_result = market_data.get('ev_model', {})

        current_price = market_data.get('price', 0)
        target_price = market_data.get('target_price', 0)

        summary = {
            'ticker': ticker,
            'current_price': current_price,
            'target_price': target_price,
            'target_price_pct': f"+{((target_price - current_price) / current_price * 100):.1f}%" if current_price and target_price and target_price > current_price else f"{((target_price - current_price) / current_price * 100):.1f}%" if current_price and target_price else None,
            'stop_loss_price': market_data.get('stop_loss_price'),
            'market_sentiment': market_data.get('market_sentiment'),
            'risk_score': risk_result.get('score'),
            'risk_level': risk_result.get('level'),
            'position_size': risk_result.get('suggested_position'),
            'ev_score': ev_result.get('ev_score'),
            'recommendation_action': ev_result.get('recommendation', {}).get('action'),
            'ai_summary': result.get('report', '')[:500] if isinstance(result.get('report'), str) else None,
            'analyzed_at': datetime.now().isoformat()
        }

        # 4. 如果是首次分析，保存到历史记录
        if is_first_time:
            try:
                from ..utils.serialization import convert_numpy_types
                analysis_history = StockAnalysisHistory(
                    user_id=g.user_id,
                    ticker=ticker,
                    style='quality',
                    current_price=convert_numpy_types(current_price),
                    target_price=convert_numpy_types(target_price),
                    stop_loss_price=convert_numpy_types(market_data.get('stop_loss_price')),
                    market_sentiment=convert_numpy_types(market_data.get('market_sentiment')),
                    risk_score=convert_numpy_types(risk_result.get('score')),
                    risk_level=risk_result.get('level'),
                    position_size=convert_numpy_types(risk_result.get('suggested_position')),
                    ev_score=convert_numpy_types(ev_result.get('ev_score')),
                    ev_weighted_pct=convert_numpy_types(ev_result.get('ev_weighted_pct')),
                    recommendation_action=ev_result.get('recommendation', {}).get('action'),
                    recommendation_confidence=ev_result.get('recommendation', {}).get('confidence'),
                    ai_summary=summary.get('ai_summary'),
                    full_analysis_data=convert_numpy_types(result)
                )
                db.session.add(analysis_history)
                db.session.commit()
                logger.info(f"首次分析已保存: {ticker} (用户: {g.user_id})")
            except Exception as e:
                logger.error(f"保存首次分析失败: {e}")
                db.session.rollback()

        return jsonify({
            'success': True,
            'summary': summary,
            'is_first_time': is_first_time,
            'from_history': False
        })

    except Exception as e:
        logger.error(f"获取股票摘要失败 {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': f'获取摘要失败: {str(e)}'}), 500
