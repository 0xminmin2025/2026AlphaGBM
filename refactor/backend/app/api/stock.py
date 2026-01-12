from flask import Blueprint, request, jsonify, g
from ..services import analysis_engine, ev_model, ai_service
from ..utils.auth import require_auth
import logging

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stock')
logger = logging.getLogger(__name__)

@stock_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze_stock():
    """
    Stock Analysis Endpoint
    Accepts: {
        "ticker": "AAPL",
        "style": "balanced",  # optional, default balanced
        "onlyHistoryData": false # optional
    }
    Returns: JSON with analysis results
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        ticker = data.get('ticker')
        if not ticker:
            return jsonify({'error': 'Ticker is required'}), 400
            
        style = data.get('style', 'balanced')
        only_history = data.get('onlyHistoryData', False)
        
        logger.info(f"Analyzing stock {ticker} with style {style} for user {getattr(g, 'user_id', 'unknown')}")
        
        # 1. Get Market Data
        market_data = analysis_engine.get_market_data(ticker, onlyHistoryData=only_history)
        if not market_data or (not market_data.get('history_prices') and not market_data.get('price')):
             return jsonify({'error': 'Failed to fetch market data'}), 500

        # If only requesting history data (e.g. for charts)
        if only_history:
             return jsonify(market_data)

        # 2. Check Liquidity
        is_liquid, liquidity_info = analysis_engine.check_liquidity(market_data)
        if not is_liquid:
            return jsonify({
                'error': 'Liquidity check failed',
                'details': liquidity_info,
                'market_data': market_data # return partial data
            }), 200 # Return 200 so frontend can handle it gracefully as a valid response
            
        # 3. Risk Analysis
        # Assuming analyze_risk_and_position returns a dict with 'score', etc.
        risk_result = analysis_engine.analyze_risk_and_position(style, market_data)
        
        # 4. EV Model
        ev_result = ev_model.calculate_ev_model(market_data, risk_result, style)
        
        # 5. AI Analysis
        # This might take time, maybe should be async or streamed?
        # For now, synchronous as per legacy app
        ai_report = ai_service.get_gemini_analysis(ticker, market_data, risk_result, ev_result, style)
        
        # 6. Construct Response
        response = {
            'ticker': ticker,
            'style': style,
            'market_data': market_data,
            'risk_analysis': risk_result,
            'ev_analysis': ev_result,
            'ai_report': ai_report,
            'liquidity': liquidity_info
        }
        
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error analyzing stock {ticker}: {e}")
        return jsonify({'error': str(e)}), 500
