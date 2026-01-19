"""
Options Module API Endpoints
Ported from new_options_module/routes.py
"""

from flask import Blueprint, jsonify, request, g
from ..services.options_service import OptionsService
from ..services.task_queue import create_analysis_task, get_task_status
from ..models import db, ServiceType, TaskType, OptionsAnalysisHistory
from ..utils.decorators import check_quota, db_retry
from ..utils.auth import require_auth, get_user_id
import logging

logger = logging.getLogger(__name__)

options_bp = Blueprint('options', __name__, url_prefix='/api/options')

def get_options_analysis_data(symbol: str, enhanced: bool = False, expiry_date: str = None, option_identifier: str = None) -> dict:
    """
    Core options analysis logic extracted for reuse in async tasks

    Args:
        symbol: Stock symbol
        enhanced: If True, perform enhanced analysis
        expiry_date: Option expiry date (for basic chain analysis)
        option_identifier: Specific option identifier (for enhanced analysis)

    Returns:
        Analysis result dictionary or error dictionary
    """
    try:
        if enhanced:
            if not option_identifier:
                return {'error': 'option_identifier is required for enhanced analysis'}

            # Enhanced analysis
            response = OptionsService.get_enhanced_analysis(symbol, option_identifier)
            return response.dict()
        else:
            if not expiry_date:
                return {'error': 'expiry_date is required for basic options chain analysis'}

            # Basic options chain analysis
            response = OptionsService.get_option_chain(symbol, expiry_date)
            return response.dict()

    except Exception as e:
        return {'error': f'Options analysis failed: {str(e)}'}

@options_bp.route('/chain-async', methods=['POST'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def analyze_options_chain_async():
    """
    Create async options chain analysis task

    Request Body:
    {
        "symbol": "AAPL",
        "expiry_date": "2024-01-19",
        "priority": 100  // optional
    }

    Returns:
    {
        "success": true,
        "task_id": "uuid-string",
        "message": "Options analysis task created successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        symbol = data.get('symbol')
        expiry_date = data.get('expiry_date')

        if not symbol or not expiry_date:
            return jsonify({'error': 'symbol and expiry_date are required'}), 400

        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Create async task
        task_id = create_analysis_task(
            user_id=user_id,
            task_type=TaskType.OPTION_ANALYSIS.value,
            input_params={
                'symbol': symbol,
                'expiry_date': expiry_date
            },
            priority=data.get('priority', 100)
        )

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Options analysis task created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': f'Failed to create options analysis task: {str(e)}'}), 500

@options_bp.route('/enhanced-async', methods=['POST'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def analyze_options_enhanced_async():
    """
    Create async enhanced options analysis task

    Request Body:
    {
        "symbol": "AAPL",
        "option_identifier": "AAPL240119C00150000",
        "expiry_date": "2024-01-19",  // optional, for history metadata
        "priority": 100  // optional
    }

    Returns:
    {
        "success": true,
        "task_id": "uuid-string",
        "message": "Enhanced options analysis task created successfully"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        symbol = data.get('symbol')
        option_identifier = data.get('option_identifier')

        if not symbol or not option_identifier:
            return jsonify({'error': 'symbol and option_identifier are required'}), 400

        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Create async task
        task_id = create_analysis_task(
            user_id=user_id,
            task_type=TaskType.ENHANCED_OPTION_ANALYSIS.value,
            input_params={
                'symbol': symbol,
                'option_identifier': option_identifier,
                'expiry_date': data.get('expiry_date')  # Optional for history
            },
            priority=data.get('priority', 100)
        )

        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': 'Enhanced options analysis task created successfully'
        }), 201

    except Exception as e:
        return jsonify({'error': f'Failed to create enhanced options analysis task: {str(e)}'}), 500

@options_bp.route('/expirations/<symbol>', methods=['GET'])
@require_auth
def get_expirations(symbol):
    """Get option expiration dates"""
    try:
        response = OptionsService.get_expirations(symbol)
        # response is an ExpirationResponse pydantic model
        return jsonify(response.dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@options_bp.route('/chain/<symbol>/<expiry_date>', methods=['GET', 'POST'])
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def get_option_chain(symbol, expiry_date):
    """
    Get option chain with scoring - supports both sync and async mode

    For async mode, send POST request with:
    {
        "async": true,
        "priority": 100  // optional
    }
    """
    try:
        # Check if async mode is requested (POST request)
        if request.method == 'POST':
            data = request.get_json() or {}
            use_async = data.get('async', False)

            if use_async:
                user_id = get_user_id()
                if not user_id:
                    return jsonify({'error': 'Authentication required for async mode'}), 401

                # Create async task
                task_id = create_analysis_task(
                    user_id=user_id,
                    task_type=TaskType.OPTION_ANALYSIS.value,
                    input_params={
                        'symbol': symbol,
                        'expiry_date': expiry_date
                    },
                    priority=data.get('priority', 100)
                )

                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'Options analysis task created successfully'
                }), 201

        # Sync mode (GET request or POST without async flag)
        result = get_options_analysis_data(symbol, enhanced=False, expiry_date=expiry_date)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@options_bp.route('/quote/<symbol>', methods=['GET'])
@require_auth
def get_quote(symbol):
    """Get basic stock quote"""
    try:
        response = OptionsService.get_stock_quote(symbol)
        return jsonify(response.dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@options_bp.route('/history/<symbol>', methods=['GET'])
@require_auth
def get_stock_history(symbol):
    """Get stock price history"""
    try:
        days = request.args.get('days', 60, type=int)
        response = OptionsService.get_stock_history(symbol, days)
        return jsonify(response), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@options_bp.route('/enhanced-analysis/<symbol>/<path:option_identifier>', methods=['GET', 'POST'])
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def get_enhanced_analysis(symbol, option_identifier):
    """
    Get enhanced analysis (VRP, Risk) - supports both sync and async mode

    For async mode, send POST request with:
    {
        "async": true,
        "priority": 100,  // optional
        "expiry_date": "2024-01-19"  // optional, for history metadata
    }
    """
    try:
        # Check if async mode is requested (POST request)
        if request.method == 'POST':
            data = request.get_json() or {}
            use_async = data.get('async', False)

            if use_async:
                user_id = get_user_id()
                if not user_id:
                    return jsonify({'error': 'Authentication required for async mode'}), 401

                # Create async task
                task_id = create_analysis_task(
                    user_id=user_id,
                    task_type=TaskType.ENHANCED_OPTION_ANALYSIS.value,
                    input_params={
                        'symbol': symbol,
                        'option_identifier': option_identifier,
                        'expiry_date': data.get('expiry_date')  # Optional for history
                    },
                    priority=data.get('priority', 100)
                )

                return jsonify({
                    'success': True,
                    'task_id': task_id,
                    'message': 'Enhanced options analysis task created successfully'
                }), 201

        # Sync mode (GET request or POST without async flag)
        result = get_options_analysis_data(symbol, enhanced=True, option_identifier=option_identifier)

        if 'error' in result:
            return jsonify({'error': result['error']}), 500

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@options_bp.route('/history', methods=['GET'])
@require_auth
@db_retry(max_retries=3, retry_delay=0.5)
def get_analysis_history():
    """
    Get user's options analysis history
    Query parameters:
    - page: Page number (default 1)
    - per_page: Items per page (default 10, max 50)
    - symbol: Filter by symbol (optional)
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)  # Max 50 per page
        symbol_filter = request.args.get('symbol', '').upper()

        query = OptionsAnalysisHistory.query.filter_by(user_id=g.user_id)

        if symbol_filter:
            query = query.filter(OptionsAnalysisHistory.symbol == symbol_filter)

        query = query.order_by(OptionsAnalysisHistory.created_at.desc())

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
                    logger.info(f"Using old format for options history item {item.id}")
                else:
                    # New format: direct analysis data (no wrapper)
                    complete_analysis = item.full_analysis_data.copy()
                    logger.info(f"Using new format for options history item {item.id}")

                # Add history metadata for list display
                complete_analysis['history_metadata'] = {
                    'id': item.id,
                    'created_at': item.created_at.isoformat(),
                    'is_from_history': True,
                    'symbol': item.symbol,
                    'option_identifier': item.option_identifier,
                    'expiry_date': item.expiry_date,
                    'analysis_type': item.analysis_type
                }

                history_items.append(complete_analysis)
            else:
                # Fallback for very old records without full_analysis_data
                logger.info(f"Using fallback format for options history item {item.id}")
                history_items.append({
                    'success': True,
                    'data': {
                        'symbol': item.symbol,
                        'option_identifier': item.option_identifier,
                        'strike_price': item.strike_price,
                        'option_type': item.option_type,
                        'option_score': item.option_score,
                        'iv_rank': item.iv_rank
                    },
                    'vrp_analysis': item.vrp_analysis,
                    'risk_analysis': item.risk_analysis,
                    'report': item.ai_summary or '历史期权分析数据',
                    'history_metadata': {
                        'id': item.id,
                        'created_at': item.created_at.isoformat(),
                        'is_from_history': True,
                        'symbol': item.symbol,
                        'option_identifier': item.option_identifier,
                        'expiry_date': item.expiry_date,
                        'analysis_type': item.analysis_type,
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
        logger.error(f"Error fetching options analysis history for user {g.user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@options_bp.route('/history/<int:history_id>', methods=['GET'])
@require_auth
@db_retry(max_retries=3, retry_delay=0.5)
def get_analysis_history_detail(history_id):
    """
    Get detailed options analysis history by ID including full analysis data
    """
    try:
        history_item = OptionsAnalysisHistory.query.filter_by(
            id=history_id,
            user_id=g.user_id
        ).first()

        if not history_item:
            return jsonify({'success': False, 'error': 'Options analysis history not found'}), 404

        # Check if we have complete analysis data
        if history_item.full_analysis_data:
            # Support both old and new data formats
            if 'complete_response' in history_item.full_analysis_data:
                # Old format: extract from complete_response wrapper
                stored_response = history_item.full_analysis_data['complete_response'].copy()
                logger.info(f"Using old format for options history detail {history_item.id}")
            else:
                # New format: direct analysis data (no wrapper)
                stored_response = history_item.full_analysis_data.copy()
                logger.info(f"Using new format for options history detail {history_item.id}")

            # Add history metadata for frontend reference
            stored_response['history_metadata'] = {
                'id': history_item.id,
                'created_at': history_item.created_at.isoformat(),
                'is_from_history': True,
                'symbol': history_item.symbol,
                'option_identifier': history_item.option_identifier,
                'expiry_date': history_item.expiry_date,
                'analysis_type': history_item.analysis_type
            }

            logger.info(f"Returning complete stored options analysis response for history ID {history_item.id}")
            return jsonify(stored_response)
        else:
            # Fallback for very old records without full_analysis_data
            logger.info(f"Using fallback format for options history ID {history_item.id}")
            detail_response = {
                'success': True,
                'data': {
                    'symbol': history_item.symbol,
                    'option_identifier': history_item.option_identifier,
                    'strike_price': history_item.strike_price,
                    'option_type': history_item.option_type,
                    'option_score': history_item.option_score,
                    'iv_rank': history_item.iv_rank
                },
                'vrp_analysis': history_item.vrp_analysis,
                'risk_analysis': history_item.risk_analysis,
                'report': history_item.ai_summary or '历史期权分析数据',
                'history_metadata': {
                    'id': history_item.id,
                    'created_at': history_item.created_at.isoformat(),
                    'is_from_history': True,
                    'symbol': history_item.symbol,
                    'option_identifier': history_item.option_identifier,
                    'expiry_date': history_item.expiry_date,
                    'analysis_type': history_item.analysis_type,
                    'incomplete_data': True
                }
            }
            return jsonify(detail_response)

    except Exception as e:
        logger.error(f"Error fetching options analysis history detail {history_id} for user {g.user_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
