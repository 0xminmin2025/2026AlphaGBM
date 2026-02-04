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


@options_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """
    获取每日热门期权推荐

    Query Parameters:
    - count: 返回推荐数量 (默认5，最大10)
    - refresh: 是否强制刷新 (默认false)

    Returns:
    {
        "success": true,
        "recommendations": [...],
        "market_summary": {...},
        "updated_at": "2024-01-21T09:30:00Z"
    }
    """
    try:
        from ..services.recommendation_service import recommendation_service

        count = request.args.get('count', 5, type=int)
        count = min(max(1, count), 10)  # 限制1-10

        force_refresh = request.args.get('refresh', 'false').lower() == 'true'

        result = recommendation_service.get_daily_recommendations(
            count=count,
            force_refresh=force_refresh
        )

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"获取推荐失败: {e}")
        return jsonify({'success': False, 'error': f'获取推荐失败: {str(e)}'}), 500


@options_bp.route('/reverse-score', methods=['POST'])
@require_auth
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1)
def reverse_score_option():
    """
    反向查分：根据用户输入的期权参数计算评分

    Request Body:
    {
        "symbol": "AAPL",
        "option_type": "CALL",  // or "PUT"
        "strike": 190,
        "expiry_date": "2024-02-16",
        "option_price": 2.50,
        "implied_volatility": 0.28  // 可选，留空自动估算
    }

    Returns:
    {
        "success": true,
        "symbol": "AAPL",
        "option_type": "CALL",
        "strike": 190,
        "expiry_date": "2024-02-16",
        "days_to_expiry": 25,
        "option_price": 2.50,
        "implied_volatility": 28.0,
        "stock_data": {...},
        "scores": {
            "sell_call": {"score": 72, "style_label": "稳健收益", ...},
            "buy_call": {"score": 65, "style_label": "激进策略", ...}
        },
        "trend_info": {...}
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        # 验证必需参数
        required_fields = ['symbol', 'option_type', 'strike', 'expiry_date', 'option_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        symbol = data.get('symbol', '').upper()
        option_type = data.get('option_type', '').upper()
        strike = float(data.get('strike', 0))
        expiry_date = data.get('expiry_date', '')
        option_price = float(data.get('option_price', 0))
        implied_volatility = data.get('implied_volatility')

        # 验证期权类型
        if option_type not in ['CALL', 'PUT']:
            return jsonify({'success': False, 'error': 'option_type must be CALL or PUT'}), 400

        # 验证数值
        if strike <= 0:
            return jsonify({'success': False, 'error': 'strike must be positive'}), 400
        if option_price <= 0:
            return jsonify({'success': False, 'error': 'option_price must be positive'}), 400

        # 验证日期格式
        try:
            from datetime import datetime
            datetime.strptime(expiry_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({'success': False, 'error': 'expiry_date must be in YYYY-MM-DD format'}), 400

        # 转换隐含波动率（如果提供的话）
        if implied_volatility is not None:
            implied_volatility = float(implied_volatility)
            # 如果用户输入的是百分比（如28），转换为小数（0.28）
            if implied_volatility > 1:
                implied_volatility = implied_volatility / 100

        # 调用服务层计算评分
        result = OptionsService.reverse_score_option(
            symbol=symbol,
            option_type=option_type,
            strike=strike,
            expiry_date=expiry_date,
            option_price=option_price,
            implied_volatility=implied_volatility
        )

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"反向查分失败: {e}")
        return jsonify({'success': False, 'error': f'反向查分失败: {str(e)}'}), 500


@options_bp.route('/chain/batch', methods=['POST'])
@require_auth
def get_option_chain_batch():
    """
    批量获取期权链 - 支持多symbol + 多expiry

    Request Body:
    {
        "symbols": ["AAPL", "TSLA"],
        "expiries": ["2024-02-16", "2024-02-23"],
        "priority": 100  // optional
    }

    计费: symbols数 × expiries数

    Returns:
    {
        "success": true,
        "task_ids": [
            {"symbol": "AAPL", "expiry": "2024-02-16", "task_id": "uuid1"},
            {"symbol": "AAPL", "expiry": "2024-02-23", "task_id": "uuid2"},
            ...
        ],
        "total_queries": 4
    }
    """
    try:
        from ..utils.decorators import check_and_deduct_quota

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        symbols = data.get('symbols', [])
        expiries = data.get('expiries', [])
        priority = data.get('priority', 100)

        # Validate inputs
        if not symbols or not isinstance(symbols, list):
            return jsonify({'error': 'symbols array is required'}), 400

        if not expiries or not isinstance(expiries, list):
            return jsonify({'error': 'expiries array is required'}), 400

        # Limit: max 2 expiry dates
        if len(expiries) > 2:
            return jsonify({'error': 'Maximum 2 expiry dates allowed'}), 400

        # Limit: max 3 symbols (consistent with existing limit)
        if len(symbols) > 3:
            return jsonify({'error': 'Maximum 3 symbols allowed'}), 400

        user_id = get_user_id()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Calculate total queries = symbols × expiries
        total_queries = len(symbols) * len(expiries)

        # Check and deduct quota in one go
        quota_result = check_and_deduct_quota(
            user_id=user_id,
            service_type=ServiceType.OPTION_ANALYSIS.value,
            amount=total_queries,
            ticker=','.join(symbols)
        )

        if not quota_result['success']:
            return jsonify({
                'error': quota_result['message'],
                'remaining_credits': quota_result['remaining'],
                'free_remaining': quota_result['free_remaining'],
                'free_quota': quota_result['free_quota'],
                'code': 'INSUFFICIENT_CREDITS'
            }), 402

        # Create async tasks for each (symbol, expiry) combination
        task_ids = []
        for symbol in symbols:
            for expiry in expiries:
                task_id = create_analysis_task(
                    user_id=user_id,
                    task_type=TaskType.OPTION_ANALYSIS.value,
                    input_params={
                        'symbol': symbol.upper(),
                        'expiry_date': expiry
                    },
                    priority=priority
                )
                task_ids.append({
                    'symbol': symbol.upper(),
                    'expiry': expiry,
                    'task_id': task_id
                })

        return jsonify({
            'success': True,
            'task_ids': task_ids,
            'total_queries': total_queries,
            'quota_info': {
                'is_free': quota_result['is_free'],
                'free_remaining': quota_result['free_remaining'],
                'free_quota': quota_result['free_quota']
            }
        }), 201

    except Exception as e:
        logger.error(f"Failed to create batch options analysis tasks: {e}")
        return jsonify({'error': f'Failed to create batch tasks: {str(e)}'}), 500


@options_bp.route('/recognize-image', methods=['POST'])
@require_auth
def recognize_option_image():
    """
    识别期权截图，提取期权参数

    Request:
    - Content-Type: multipart/form-data
    - image: 图片文件 (PNG, JPG, JPEG, WebP)

    Returns:
    {
        "success": true,
        "data": {
            "symbol": "AAPL",
            "option_type": "CALL",
            "strike": 230,
            "expiry_date": "2025-02-21",
            "option_price": 5.50,
            "implied_volatility": 0.28,
            "confidence": "high",
            "notes": "识别备注"
        }
    }
    """
    try:
        from ..services.image_recognition_service import image_recognition_service

        # 检查是否有上传的文件
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '请上传图片文件'}), 400

        file = request.files['image']

        if file.filename == '':
            return jsonify({'success': False, 'error': '未选择文件'}), 400

        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''

        if file_ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'不支持的文件格式。支持: {", ".join(allowed_extensions)}'
            }), 400

        # 检查文件大小 (限制 10MB)
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头

        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({'success': False, 'error': '文件大小不能超过 10MB'}), 400

        # 读取文件内容
        image_data = file.read()

        # 确定 MIME 类型
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'webp': 'image/webp'
        }
        mime_type = mime_types.get(file_ext, 'image/png')

        # 调用识别服务
        result = image_recognition_service.recognize_option_from_image(image_data, mime_type)

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"图片识别失败: {e}")
        return jsonify({'success': False, 'error': f'图片识别失败: {str(e)}'}), 500
