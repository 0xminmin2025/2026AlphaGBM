"""
Paper Trading API Endpoints

Public read endpoints for performance display.
Admin-protected write endpoints for manual triggers.
"""

import os
import logging
from flask import Blueprint, request, jsonify

from ..models import db, PaperPerformance
from ..services.paper_trading_service import paper_trading_service

logger = logging.getLogger(__name__)

trading_bp = Blueprint('trading', __name__, url_prefix='/api/trading')


def _check_admin_key():
    """Verify admin key for protected endpoints."""
    admin_key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
    expected_key = os.environ.get('ADMIN_SECRET_KEY', '')
    if not expected_key or admin_key != expected_key:
        return False
    return True


@trading_bp.route('/performance', methods=['GET'])
def get_performance():
    """
    Get daily NAV series for equity curve display.

    Query params:
        strategy: momentum|options_seller|combined (default: combined)
        period: 1m|3m|6m|1y|all (default: all)
    """
    strategy = request.args.get('strategy', 'combined')
    period = request.args.get('period', 'all')

    query = PaperPerformance.query.filter_by(strategy=strategy)

    # Period filter
    if period != 'all':
        from datetime import date, timedelta
        today = date.today()
        period_days = {'1m': 30, '3m': 90, '6m': 180, '1y': 365}
        days = period_days.get(period, 365)
        start_date = today - timedelta(days=days)
        query = query.filter(PaperPerformance.date >= start_date)

    performances = query.order_by(PaperPerformance.date.asc()).all()

    return jsonify({
        'success': True,
        'strategy': strategy,
        'period': period,
        'data': [p.to_dict() for p in performances],
        'count': len(performances),
    })


@trading_bp.route('/performance/summary', methods=['GET'])
def get_performance_summary():
    """Get KPI summary metrics."""
    summary = paper_trading_service.get_performance_summary()
    return jsonify({
        'success': True,
        **summary,
    })


@trading_bp.route('/positions', methods=['GET'])
def get_positions():
    """Get current open paper positions."""
    strategy = request.args.get('strategy')
    positions = paper_trading_service.get_positions(strategy=strategy)
    return jsonify({
        'success': True,
        'positions': positions,
        'count': len(positions),
    })


@trading_bp.route('/trades', methods=['GET'])
def get_trades():
    """Get trade history with pagination."""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    strategy = request.args.get('strategy')
    result = paper_trading_service.get_trades(limit=limit, offset=offset, strategy=strategy)
    return jsonify({
        'success': True,
        **result,
    })


@trading_bp.route('/status', methods=['GET'])
def get_status():
    """Get paper trading engine status."""
    status = paper_trading_service.get_status()
    return jsonify({
        'success': True,
        **status,
    })


@trading_bp.route('/rebalance', methods=['POST'])
def trigger_rebalance():
    """
    Manually trigger momentum rebalance.
    Requires admin key.
    """
    if not _check_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from ..services.paper_strategies import run_momentum_rebalance
        run_momentum_rebalance()
        return jsonify({
            'success': True,
            'message': 'Momentum rebalance completed',
        })
    except Exception as e:
        logger.error(f"Manual rebalance failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@trading_bp.route('/options-scan', methods=['POST'])
def trigger_options_scan():
    """
    Manually trigger weekly options scan.
    Requires admin key.
    """
    if not _check_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        from ..services.paper_strategies import run_weekly_options_scan
        run_weekly_options_scan()
        return jsonify({
            'success': True,
            'message': 'Options scan completed',
        })
    except Exception as e:
        logger.error(f"Manual options scan failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@trading_bp.route('/daily-snapshot', methods=['POST'])
def trigger_daily_snapshot():
    """
    Manually trigger daily performance snapshot.
    Requires admin key.
    """
    if not _check_admin_key():
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        paper_trading_service.update_prices()
        paper_trading_service.check_stop_losses()
        paper_trading_service.check_option_expiry()
        paper_trading_service.calculate_daily_performance()
        return jsonify({
            'success': True,
            'message': 'Daily snapshot completed',
        })
    except Exception as e:
        logger.error(f"Manual daily snapshot failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
