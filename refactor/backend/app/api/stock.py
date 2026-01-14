from flask import Blueprint, request, jsonify, g
from ..services import analysis_engine, ev_model, ai_service
from ..services.task_queue import create_analysis_task, get_task_status
from ..utils.auth import require_auth, get_user_id
from ..utils.decorators import check_quota
from ..utils.serialization import convert_numpy_types
from ..models import db, ServiceType, StockAnalysisHistory, TaskType
import yfinance as yf
import logging
import json
from datetime import datetime

stock_bp = Blueprint('stock', __name__, url_prefix='/api/stock')
logger = logging.getLogger(__name__)

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

        return response

    except Exception as e:
        logger.error(f"Error in stock analysis for {ticker}: {e}")
        return {'error': f'分析过程中发生错误: {str(e)}'}

@stock_bp.route('/analyze-async', methods=['POST'])
@require_auth
@check_quota(service_type=ServiceType.STOCK_ANALYSIS.value, amount=1)
def analyze_stock_async():
    """
    Create async stock analysis task

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

        # Create async task
        task_id = create_analysis_task(
            user_id=user_id,
            task_type=TaskType.STOCK_ANALYSIS.value,
            input_params={
                'ticker': ticker,
                'style': style
            },
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
    Stock Analysis Endpoint - Supports both sync and async mode

    Accepts: {
        "ticker": "AAPL",
        "style": "quality",  # optional, default quality
        "onlyHistoryData": false, # optional
        "async": false  # optional, if true creates async task
    }

    Returns:
    - Sync mode: JSON with analysis results in original format
    - Async mode: {"success": true, "task_id": "uuid", "message": "..."}
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
        use_async = data.get('async', False)

        logger.info(f"Analyzing stock {ticker} with style {style} for user {getattr(g, 'user_id', 'unknown')} (async: {use_async})")

        # Check if async mode is requested
        if use_async:
            user_id = get_user_id()
            if not user_id:
                return jsonify({'success': False, 'error': 'Authentication required for async mode'}), 401

            # Create async task
            task_id = create_analysis_task(
                user_id=user_id,
                task_type=TaskType.STOCK_ANALYSIS.value,
                input_params={
                    'ticker': ticker,
                    'style': style
                },
                priority=data.get('priority', 100)
            )

            logger.info(f"Created async stock analysis task {task_id} for {ticker} ({style}) - User: {user_id}")

            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Analysis task created successfully'
            }), 201

        # Sync mode - use the extracted helper function
        result = get_stock_analysis_data(ticker, style, only_history)

        # Handle errors from helper function
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400

        # If only requesting history data, return it directly
        if only_history:
            return jsonify({'success': True, 'data': result})

        # For full analysis, result already contains the complete response
        response = result

        # 7. Save analysis results to history
        if not only_history:  # Only save history for full analysis, not just chart data
            try:
                # Check if user_id is available
                if not hasattr(g, 'user_id') or not g.user_id:
                    logger.error(f"No user_id available in Flask globals for history saving")
                    return jsonify(response)  # Return response without saving history

                # Extract key data for storage from the result
                market_data = response.get('data', {})
                risk_result = response.get('risk', {})
                ai_report = response.get('report', '')
                ev_result = market_data.get('ev_model', {})

                logger.info(f"Preparing to save analysis history for {ticker} (user: {g.user_id})")

                # Extract summary from AI report for quick preview (first 1000 chars)
                ai_summary = None
                if isinstance(ai_report, dict):
                    ai_summary = ai_report.get('summary', '')[:1000] if ai_report.get('summary') else None
                elif isinstance(ai_report, str):
                    ai_summary = ai_report[:1000] if ai_report else None

                # Store the COMPLETE backend response as-is for perfect recreation
                # This ensures 100% compatibility with frontend display logic
                complete_analysis_data = {
                    'original_request': {
                        'ticker': ticker,
                        'style': style,
                        'timestamp': datetime.utcnow().isoformat(),
                        'user_id': g.user_id
                    },
                    'complete_response': response,  # Store the exact response sent to frontend
                    'version': '1.0'  # Version for future compatibility
                }

                # Convert all numpy types to Python native types before JSON serialization
                # This prevents PostgreSQL schema errors when storing JSON data
                complete_analysis_data_clean = convert_numpy_types(complete_analysis_data)

                analysis_history = StockAnalysisHistory(
                    user_id=g.user_id,
                    ticker=ticker,
                    style=style,
                    # Extract key fields for indexing and quick display - also convert numpy types
                    current_price=convert_numpy_types(market_data.get('price')),
                    target_price=convert_numpy_types(market_data.get('target_price')),
                    stop_loss_price=convert_numpy_types(market_data.get('stop_loss_price')),
                    market_sentiment=convert_numpy_types(market_data.get('market_sentiment')),
                    risk_score=convert_numpy_types(risk_result.get('score')),
                    risk_level=risk_result.get('level'),  # String field, no need to convert
                    position_size=convert_numpy_types(risk_result.get('suggested_position')),
                    ev_score=convert_numpy_types(ev_result.get('ev_score')),
                    ev_weighted_pct=convert_numpy_types(ev_result.get('ev_weighted_pct')),
                    recommendation_action=ev_result.get('recommendation', {}).get('action'),  # String field
                    recommendation_confidence=ev_result.get('recommendation', {}).get('confidence'),  # String field
                    ai_summary=ai_summary,
                    # Store the COMPLETE response for perfect frontend recreation
                    full_analysis_data=complete_analysis_data_clean
                )

                logger.info(f"Adding analysis history to database session...")
                db.session.add(analysis_history)

                logger.info(f"Committing analysis history to database...")
                db.session.commit()

                logger.info(f"Successfully saved analysis history for {ticker} (user: {g.user_id}, id: {analysis_history.id})")

            except Exception as e:
                logger.error(f"Failed to save analysis history for {ticker}: {str(e)}")
                import traceback
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Don't fail the entire request if history saving fails
                db.session.rollback()

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error analyzing stock {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'分析过程中发生错误: {str(e)}'}), 500


@stock_bp.route('/history', methods=['GET'])
@require_auth
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
            if item.full_analysis_data and 'complete_response' in item.full_analysis_data:
                # Use the stored complete response data
                complete_analysis = item.full_analysis_data['complete_response'].copy()

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
                # Fallback for old format data
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

        # Check if we have the new complete response format
        if history_item.full_analysis_data and 'complete_response' in history_item.full_analysis_data:
            # Return the stored complete response exactly as it was sent to frontend originally
            stored_response = history_item.full_analysis_data['complete_response']

            # Add history metadata for frontend reference
            stored_response['history_metadata'] = {
                'id': history_item.id,
                'created_at': history_item.created_at.isoformat(),
                'is_from_history': True
            }

            logger.info(f"Returning complete stored analysis response for history ID {history_item.id}")
            return jsonify(stored_response)
        else:
            # Fallback for old format data (compatibility)
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
