"""
板块分析API路由

提供板块轮动分析和资金结构分析的API端点
"""

from flask import Blueprint, request, jsonify, g
from ..utils.auth import require_auth
from ..services.sector_rotation_service import get_sector_rotation_service
from ..services.capital_structure_service import get_capital_structure_service
import logging

sector_bp = Blueprint('sector', __name__, url_prefix='/api/sector')
logger = logging.getLogger(__name__)


# ==================== 板块轮动分析 ====================

@sector_bp.route('/rotation/overview', methods=['GET'])
def get_rotation_overview():
    """
    获取板块轮动概览

    Query Parameters:
        market: 市场代码 (US/HK/CN)，默认US

    Returns:
        板块轮动概览，包含所有板块强度排名
    """
    try:
        market = request.args.get('market', 'US').upper()
        if market not in ['US', 'HK', 'CN']:
            market = 'US'

        service = get_sector_rotation_service()
        result = service.get_rotation_overview(market)

        return jsonify({
            'success': True,
            **result
        })

    except Exception as e:
        logger.error(f"获取板块轮动概览失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/rotation/sector/<sector_name>', methods=['GET'])
def get_sector_detail(sector_name: str):
    """
    获取单板块详情

    Path Parameters:
        sector_name: 板块名称

    Query Parameters:
        market: 市场代码 (US/HK/CN)

    Returns:
        板块详细分析
    """
    try:
        market = request.args.get('market', 'US').upper()

        service = get_sector_rotation_service()
        result = service.get_sector_detail(sector_name, market)

        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 404

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取板块详情失败 {sector_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/stock/<ticker>/sector-analysis', methods=['GET'])
def analyze_stock_sector(ticker: str):
    """
    分析个股板块关联

    Path Parameters:
        ticker: 股票代码

    Query Parameters:
        sector: 股票所属板块（可选，如未提供将尝试自动获取）
        industry: 股票所属行业（可选）
        market: 市场代码

    Returns:
        个股板块同步度分析
    """
    try:
        ticker = ticker.upper()
        sector = request.args.get('sector', 'Technology')
        industry = request.args.get('industry')
        market = request.args.get('market', 'US').upper()

        service = get_sector_rotation_service()
        result = service.analyze_stock_sector(
            ticker=ticker,
            sector=sector,
            industry=industry,
            market=market
        )

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"分析个股板块失败 {ticker}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/heatmap', methods=['GET'])
def get_heatmap():
    """
    获取板块热力图数据

    Query Parameters:
        market: 市场代码 (US/HK/CN)

    Returns:
        热力图数据列表
    """
    try:
        market = request.args.get('market', 'US').upper()

        service = get_sector_rotation_service()
        result = service.get_heatmap_data(market)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取热力图数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/top-sectors', methods=['GET'])
def get_top_sectors():
    """
    获取强势板块排行

    Query Parameters:
        market: 市场代码
        limit: 返回数量（默认5）

    Returns:
        强势板块列表
    """
    try:
        market = request.args.get('market', 'US').upper()
        limit = request.args.get('limit', 5, type=int)
        limit = min(max(limit, 1), 20)

        service = get_sector_rotation_service()
        result = service.get_top_sectors(market, limit)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取强势板块失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/bottom-sectors', methods=['GET'])
def get_bottom_sectors():
    """
    获取弱势板块排行

    Query Parameters:
        market: 市场代码
        limit: 返回数量（默认5）

    Returns:
        弱势板块列表
    """
    try:
        market = request.args.get('market', 'US').upper()
        limit = request.args.get('limit', 5, type=int)
        limit = min(max(limit, 1), 20)

        service = get_sector_rotation_service()
        result = service.get_bottom_sectors(market, limit)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取弱势板块失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/available-sectors', methods=['GET'])
def get_available_sectors():
    """
    获取可用板块列表

    Query Parameters:
        market: 市场代码

    Returns:
        板块列表
    """
    try:
        market = request.args.get('market', 'US').upper()

        service = get_sector_rotation_service()
        result = service.get_available_sectors(market)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取板块列表失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 资金结构分析 ====================

@sector_bp.route('/capital/analysis/<ticker>', methods=['GET'])
def analyze_capital_structure(ticker: str):
    """
    分析个股资金结构

    Path Parameters:
        ticker: 股票代码

    Returns:
        资金结构分析结果
    """
    try:
        ticker = ticker.upper()

        service = get_capital_structure_service()
        result = service.analyze_stock_capital(ticker)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"分析资金结构失败 {ticker}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/capital/factor/<ticker>', methods=['GET'])
def get_capital_factor(ticker: str):
    """
    获取资金因子（快速接口）

    Path Parameters:
        ticker: 股票代码

    Returns:
        资金因子值
    """
    try:
        ticker = ticker.upper()

        service = get_capital_structure_service()
        factor = service.get_capital_factor(ticker)

        return jsonify({
            'success': True,
            'ticker': ticker,
            'capital_factor': factor
        })

    except Exception as e:
        logger.error(f"获取资金因子失败 {ticker}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/capital/stage/<ticker>', methods=['GET'])
def get_propagation_stage(ticker: str):
    """
    获取情绪传导阶段

    Path Parameters:
        ticker: 股票代码

    Returns:
        阶段信息
    """
    try:
        ticker = ticker.upper()

        service = get_capital_structure_service()
        result = service.get_propagation_stage(ticker)

        return jsonify({
            'success': True,
            'ticker': ticker,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取传导阶段失败 {ticker}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/capital/stages', methods=['GET'])
def get_all_stages():
    """
    获取所有情绪传导阶段定义

    Returns:
        阶段定义列表
    """
    try:
        service = get_capital_structure_service()
        result = service.get_all_stages()

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        logger.error(f"获取阶段定义失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@sector_bp.route('/capital/signals/<ticker>', methods=['GET'])
def get_capital_signals(ticker: str):
    """
    获取资金集中度信号

    Path Parameters:
        ticker: 股票代码

    Returns:
        信号列表
    """
    try:
        ticker = ticker.upper()

        service = get_capital_structure_service()
        signals = service.get_concentration_signals(ticker)

        return jsonify({
            'success': True,
            'ticker': ticker,
            'signals': signals
        })

    except Exception as e:
        logger.error(f"获取资金信号失败 {ticker}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 管理接口 ====================

@sector_bp.route('/cache/clear', methods=['POST'])
@require_auth
def clear_cache():
    """
    清除缓存（需要认证）

    Request Body (optional):
        market: 指定市场
        ticker: 指定股票

    Returns:
        操作结果
    """
    try:
        data = request.get_json() or {}
        market = data.get('market')
        ticker = data.get('ticker')

        sector_service = get_sector_rotation_service()
        capital_service = get_capital_structure_service()

        sector_service.clear_cache(market)
        capital_service.clear_cache(ticker)

        return jsonify({
            'success': True,
            'message': '缓存已清除'
        })

    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
