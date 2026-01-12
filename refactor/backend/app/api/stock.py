from flask import Blueprint, request, jsonify, g
from ..services import analysis_engine, ev_model, ai_service
from ..utils.auth import require_auth
import yfinance as yf
import logging

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stock')
logger = logging.getLogger(__name__)

@stock_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze_stock():
    """
    Stock Analysis Endpoint - Matching original app.py implementation
    Accepts: {
        "ticker": "AAPL",
        "style": "quality",  # optional, default quality
        "onlyHistoryData": false # optional
    }
    Returns: JSON with analysis results in original format
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
        
        logger.info(f"Analyzing stock {ticker} with style {style} for user {getattr(g, 'user_id', 'unknown')}")
        
        # 1. Get Market Data
        market_data = analysis_engine.get_market_data(ticker, onlyHistoryData=only_history)
        if not market_data or not market_data.get('price'):
            error_msg = f'找不到股票代码 "{ticker}" 或数据获取失败'
            return jsonify({'success': False, 'error': error_msg}), 400

        # If only requesting history data (e.g. for charts)
        if only_history:
            return jsonify({'success': True, 'data': market_data})

        # 2. Risk Analysis (Matching original: analyze_risk_and_position)
        try:
            risk_result = analysis_engine.analyze_risk_and_position(style, market_data)
        except Exception as e:
            logger.error(f"计算风险评分时发生异常: {e}")
            return jsonify({'success': False, 'error': f'风险计算失败: {str(e)}'}), 500
        
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
        except Exception as e:
            logger.warning(f"计算目标价格时发生异常: {e}")
            market_data['target_price'] = market_data.get('price', 0)  # Default to current price
        
        # 4.5 Calculate Dynamic Stop Loss (Matching original - ATR based)
        try:
            # Get 1-month history for ATR calculation
            normalized_ticker = analysis_engine.normalize_ticker(ticker)
            stock = yf.Ticker(normalized_ticker)
            hist = stock.history(period="1mo", timeout=10)
            
            if not hist.empty and len(hist) >= 15:
                # Use ATR dynamic stop loss
                stop_loss_price = analysis_engine.calculate_atr_stop_loss(
                    buy_price=market_data['price'],
                    hist_data=hist,
                    atr_period=14,
                    atr_multiplier=2.5,
                    min_stop_loss_pct=0.05,
                    beta=market_data.get('beta')
                )
                market_data['stop_loss_price'] = stop_loss_price
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
        
        # 4.6 Calculate EV Model (Matching original)
        try:
            ev_result = ev_model.calculate_ev_model(market_data, risk_result, style)
            market_data['ev_model'] = ev_result
            logger.info(f"EV模型计算完成: {ticker}, 加权EV={ev_result.get('ev_weighted_pct', 0):.2f}%")
        except Exception as e:
            logger.warning(f"计算EV模型时发生异常: {e}")
            market_data['ev_model'] = {
                'error': str(e),
                'ev_weighted': 0.0,
                'ev_weighted_pct': 0.0,
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
        
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error analyzing stock {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'分析过程中发生错误: {str(e)}'}), 500
