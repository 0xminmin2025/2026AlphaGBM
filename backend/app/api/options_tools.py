"""
期权高级工具 API 端点

提供：
- Greeks 计算器
- 波动率微笑 & 3D 曲面
- 策略构建器
- P/L 模拟器
- 期权扫描器
"""

from flask import Blueprint, jsonify, request
from ..utils.auth import require_auth, get_user_id
from ..utils.decorators import check_quota
from ..models import ServiceType
from ..analysis.options_analysis.core.greeks_calculator import (
    BlackScholesCalculator, OptionLeg
)
from ..analysis.options_analysis.advanced.vol_surface import VolatilitySurfaceAnalyzer
from ..analysis.options_analysis.advanced.strategy_composer import StrategyComposer
from ..analysis.options_analysis.advanced.pnl_simulator import PnLSimulator
from ..analysis.options_analysis.scanner.option_scanner import (
    OptionScanner, ScanFilter
)
import logging

logger = logging.getLogger(__name__)

options_tools_bp = Blueprint('options_tools', __name__, url_prefix='/api/options/tools')

# 单例
_bs_calculator = BlackScholesCalculator()
_vol_analyzer = VolatilitySurfaceAnalyzer()
_strategy_composer = StrategyComposer()
_pnl_simulator = PnLSimulator()
_option_scanner = OptionScanner()


# ─────────────────────────────────────
# Greeks 计算器
# ─────────────────────────────────────

@options_tools_bp.route('/greeks', methods=['POST'])
@require_auth
def calculate_greeks():
    """
    计算单个期权的 Greeks

    Request Body:
    {
        "spot": 150.0,
        "strike": 155.0,
        "expiry_days": 30,
        "iv": 0.25,
        "option_type": "call",
        "risk_free_rate": 0.05  // optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        spot = data.get('spot')
        strike = data.get('strike')
        expiry_days = data.get('expiry_days')
        iv = data.get('iv')
        option_type = data.get('option_type', 'call')

        if not all([spot, strike, expiry_days is not None, iv]):
            return jsonify({'error': '缺少必要参数: spot, strike, expiry_days, iv'}), 400

        rfr = data.get('risk_free_rate', 0.05)
        calc = BlackScholesCalculator(risk_free_rate=rfr)

        result = calc.calculate(
            S=float(spot),
            K=float(strike),
            expiry_days=int(expiry_days),
            sigma=float(iv),
            option_type=option_type
        )

        return jsonify({'success': True, 'data': result.to_dict()})

    except Exception as e:
        logger.error(f"Greeks 计算失败: {e}")
        return jsonify({'error': f'计算失败: {str(e)}'}), 500


@options_tools_bp.route('/implied-volatility', methods=['POST'])
@require_auth
def calculate_iv():
    """
    从市场价格反求隐含波动率

    Request Body:
    {
        "market_price": 4.50,
        "spot": 150.0,
        "strike": 155.0,
        "expiry_days": 30,
        "option_type": "call"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        market_price = data.get('market_price')
        spot = data.get('spot')
        strike = data.get('strike')
        expiry_days = data.get('expiry_days')
        option_type = data.get('option_type', 'call')

        if not all([market_price, spot, strike, expiry_days is not None]):
            return jsonify({'error': '缺少必要参数'}), 400

        iv = _bs_calculator.implied_volatility(
            market_price=float(market_price),
            S=float(spot),
            K=float(strike),
            expiry_days=int(expiry_days),
            option_type=option_type
        )

        if iv is None:
            return jsonify({'error': '无法计算隐含波动率（价格低于内在价值或无法收敛）'}), 400

        return jsonify({
            'success': True,
            'data': {
                'implied_volatility': iv,
                'iv_pct': round(iv * 100, 2),
            }
        })

    except Exception as e:
        logger.error(f"IV 计算失败: {e}")
        return jsonify({'error': f'计算失败: {str(e)}'}), 500


# ─────────────────────────────────────
# 波动率微笑 & 曲面
# ─────────────────────────────────────

@options_tools_bp.route('/vol-smile/<symbol>', methods=['GET'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def get_vol_smile(symbol: str):
    """
    获取 2D 波动率微笑

    Query params:
        expiry: 到期日 YYYY-MM-DD（必填）
    """
    try:
        expiry = request.args.get('expiry')
        if not expiry:
            return jsonify({'error': '缺少 expiry 参数'}), 400

        # 获取期权链数据
        from ..services.options_service import OptionsService
        chain_response = OptionsService.get_option_chain(symbol, expiry)

        if not chain_response or not chain_response.success:
            return jsonify({'error': f'无法获取 {symbol} 期权链数据'}), 404

        chain_data = chain_response.dict() if hasattr(chain_response, 'dict') else {}
        underlying_price = chain_data.get('underlying_price', 0)

        calls = chain_data.get('calls', [])
        puts = chain_data.get('puts', [])

        if not calls and not puts:
            return jsonify({'error': '期权链数据为空'}), 404

        smile = _vol_analyzer.build_vol_smile(
            symbol=symbol,
            underlying_price=underlying_price,
            calls_data=calls,
            puts_data=puts,
            expiry=expiry
        )

        return jsonify({'success': True, 'data': smile.to_dict()})

    except Exception as e:
        logger.error(f"波动率微笑获取失败: {e}")
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


@options_tools_bp.route('/vol-surface/<symbol>', methods=['GET'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def get_vol_surface(symbol: str):
    """
    获取 3D 波动率曲面

    Query params:
        range: 到期范围 'all' | '30d' | '90d'（可选，默认 all）
    """
    try:
        exp_range = request.args.get('range', 'all')

        # 获取多个到期日的期权链
        from ..services.options_service import OptionsService
        expiries = OptionsService.get_available_expiries(symbol)

        if not expiries:
            return jsonify({'error': f'无法获取 {symbol} 到期日列表'}), 404

        chain_by_expiry = {}
        underlying_price = 0

        for expiry in expiries[:8]:  # 限制最多 8 个到期日
            try:
                chain_response = OptionsService.get_option_chain(symbol, expiry)
                if chain_response and chain_response.success:
                    data = chain_response.dict() if hasattr(chain_response, 'dict') else {}
                    if not underlying_price:
                        underlying_price = data.get('underlying_price', 0)
                    chain_by_expiry[expiry] = {
                        'calls': data.get('calls', []),
                        'puts': data.get('puts', []),
                    }
            except Exception:
                continue

        if not chain_by_expiry:
            return jsonify({'error': '无法获取足够的期权链数据'}), 404

        surface = _vol_analyzer.build_vol_surface(
            symbol=symbol,
            underlying_price=underlying_price,
            chain_by_expiry=chain_by_expiry
        )

        return jsonify({'success': True, 'data': surface.to_dict()})

    except Exception as e:
        logger.error(f"波动率曲面获取失败: {e}")
        return jsonify({'error': f'获取失败: {str(e)}'}), 500


# ─────────────────────────────────────
# 策略构建器
# ─────────────────────────────────────

@options_tools_bp.route('/strategy/templates', methods=['GET'])
@require_auth
def get_strategy_templates():
    """获取所有策略模板列表"""
    templates = _strategy_composer.get_templates()
    return jsonify({'success': True, 'data': templates})


@options_tools_bp.route('/strategy/build', methods=['POST'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def build_strategy():
    """
    从模板或自定义腿构建策略

    Request Body (模板模式):
    {
        "mode": "template",
        "template_id": "bull_call_spread",
        "spot": 150.0,
        "expiry_days": 30,
        "strikes": [140, 145, 150, 155, 160],
        "ivs": {"145": 0.26, "150": 0.25}  // optional
    }

    Request Body (自定义模式):
    {
        "mode": "custom",
        "spot": 150.0,
        "legs": [
            {"action": "buy", "option_type": "call", "strike": 145, "expiry_days": 30, "iv": 0.26},
            {"action": "sell", "option_type": "call", "strike": 150, "expiry_days": 30, "iv": 0.25}
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        spot = float(data.get('spot', 0))
        if spot <= 0:
            return jsonify({'error': '标的价格 (spot) 必须大于 0'}), 400

        mode = data.get('mode', 'custom')

        if mode == 'template':
            template_id = data.get('template_id')
            if not template_id:
                return jsonify({'error': '模板模式需要 template_id'}), 400

            strikes = [float(s) for s in data.get('strikes', [])]
            if not strikes:
                return jsonify({'error': '需要提供可用行权价列表 (strikes)'}), 400

            expiry_days = int(data.get('expiry_days', 30))

            # 解析 IV map
            ivs = {}
            raw_ivs = data.get('ivs', {})
            for k, v in raw_ivs.items():
                ivs[float(k)] = float(v)

            result = _strategy_composer.build_from_template(
                template_id=template_id,
                spot=spot,
                expiry_days=expiry_days,
                strikes=strikes,
                ivs=ivs if ivs else None,
                quantity=int(data.get('quantity', 1)),
                multiplier=int(data.get('multiplier', 100)),
            )

        else:
            # 自定义腿
            legs_data = data.get('legs', [])
            if not legs_data:
                return jsonify({'error': '自定义模式需要至少一个期权腿 (legs)'}), 400

            legs = []
            for ld in legs_data:
                legs.append(OptionLeg(
                    option_type=ld['option_type'],
                    strike=float(ld['strike']),
                    expiry_days=int(ld.get('expiry_days', 30)),
                    action=ld['action'],
                    quantity=int(ld.get('quantity', 1)),
                    iv=float(ld['iv']) if ld.get('iv') else None,
                    premium=float(ld['premium']) if ld.get('premium') else None,
                    multiplier=int(ld.get('multiplier', 100)),
                ))

            result = _strategy_composer.analyze_strategy(legs, spot)

        return jsonify({'success': True, 'data': result})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"策略构建失败: {e}")
        return jsonify({'error': f'构建失败: {str(e)}'}), 500


# ─────────────────────────────────────
# P/L 模拟器
# ─────────────────────────────────────

@options_tools_bp.route('/simulate', methods=['POST'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def simulate_pnl():
    """
    P/L 场景模拟

    Request Body:
    {
        "symbol": "AAPL",
        "spot": 150.0,
        "legs": [
            {"action": "buy", "option_type": "call", "strike": 145, "expiry_days": 30, "iv": 0.26},
            {"action": "sell", "option_type": "call", "strike": 150, "expiry_days": 30, "iv": 0.25}
        ],
        "future_day": 15,        // optional
        "iv_shift": 0.05,        // optional
        "price_range_pct": 0.20  // optional
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400

        spot = float(data.get('spot', 0))
        if spot <= 0:
            return jsonify({'error': 'spot 必须大于 0'}), 400

        legs_data = data.get('legs', [])
        if not legs_data:
            return jsonify({'error': '至少需要一个期权腿'}), 400

        legs = []
        for ld in legs_data:
            legs.append(OptionLeg(
                option_type=ld['option_type'],
                strike=float(ld['strike']),
                expiry_days=int(ld.get('expiry_days', 30)),
                action=ld['action'],
                quantity=int(ld.get('quantity', 1)),
                iv=float(ld['iv']) if ld.get('iv') else None,
                premium=float(ld['premium']) if ld.get('premium') else None,
                multiplier=int(ld.get('multiplier', 100)),
            ))

        result = _pnl_simulator.simulate(
            legs=legs,
            spot=spot,
            symbol=data.get('symbol', ''),
            future_day=data.get('future_day'),
            iv_shift=float(data.get('iv_shift', 0)),
            price_range_pct=float(data.get('price_range_pct', 0.20)),
        )

        response_data = result.to_dict()

        # 如果请求了热力图
        if data.get('include_heatmap'):
            heatmap = _pnl_simulator.generate_greeks_heatmap(legs, spot)
            response_data['greeks_heatmap'] = heatmap

        return jsonify({'success': True, 'data': response_data})

    except Exception as e:
        logger.error(f"P/L 模拟失败: {e}")
        return jsonify({'error': f'模拟失败: {str(e)}'}), 500


# ─────────────────────────────────────
# 期权扫描器
# ─────────────────────────────────────

@options_tools_bp.route('/scan', methods=['POST'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def scan_options():
    """
    期权机会扫描

    Request Body:
    {
        "strategies": ["covered_call", "cash_secured_put"],
        "tickers": ["AAPL", "NVDA"],        // optional, default: universe
        "iv_percentile_min": 30,              // optional
        "min_yield_pct": 1.0,                 // optional
        "expiry_range": "monthly",            // optional
        "max_results": 50                     // optional
    }
    """
    try:
        data = request.get_json() or {}

        scan_filter = ScanFilter(
            strategies=data.get('strategies', ['covered_call']),
            tickers=data.get('tickers'),
            iv_percentile_min=float(data.get('iv_percentile_min', 0)),
            iv_percentile_max=float(data.get('iv_percentile_max', 100)),
            min_yield_pct=float(data.get('min_yield_pct', 0)),
            expiry_range=data.get('expiry_range', 'monthly'),
            min_volume=int(data.get('min_volume', 10)),
            min_open_interest=int(data.get('min_open_interest', 100)),
            max_results=int(data.get('max_results', 50)),
        )

        # 数据提供函数：接入现有 OptionsService
        def chain_provider(ticker: str):
            try:
                from ..services.options_service import OptionsService
                expiries = OptionsService.get_available_expiries(ticker)
                if not expiries:
                    return None

                chains = []
                underlying_price = 0

                for expiry in expiries[:3]:  # 限制每个标的最多 3 个到期日
                    try:
                        response = OptionsService.get_option_chain(ticker, expiry)
                        if response and response.success:
                            data = response.dict() if hasattr(response, 'dict') else {}
                            if not underlying_price:
                                underlying_price = data.get('underlying_price', 0)

                            # 计算到期天数
                            from datetime import datetime
                            exp_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                            days = (exp_date - datetime.now().date()).days

                            chains.append({
                                'expiry': expiry,
                                'expiry_days': days,
                                'calls': data.get('calls', []),
                                'puts': data.get('puts', []),
                            })
                    except Exception:
                        continue

                return {
                    'underlying_price': underlying_price,
                    'chains': chains
                }
            except Exception as e:
                logger.warning(f"获取 {ticker} 数据失败: {e}")
                return None

        result = _option_scanner.scan(
            scan_filter=scan_filter,
            chain_data_provider=chain_provider
        )

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        logger.error(f"期权扫描失败: {e}")
        return jsonify({'error': f'扫描失败: {str(e)}'}), 500
