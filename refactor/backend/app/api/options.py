"""
Options Module API Endpoints
Ported from new_options_module/routes.py
"""

from flask import Blueprint, jsonify, request, g
from ..services.options_service import OptionsService
from ..services.task_queue import create_analysis_task, get_task_status
from ..models import ServiceType, TaskType
from ..utils.decorators import check_quota
from ..utils.auth import require_auth, get_user_id

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
