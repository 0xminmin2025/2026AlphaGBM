from flask import Blueprint, jsonify, request, g
from ..utils.auth import require_auth, get_user_id
from ..models import User, Watchlist, Alert, db
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/api/user')


@user_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    return jsonify({'message': 'User Profile Endpoint'})


# ─────────────────────────────────────
# Watchlist
# ─────────────────────────────────────

@user_bp.route('/watchlist', methods=['GET'])
@require_auth
def get_watchlist():
    try:
        user_id = get_user_id()
        items = Watchlist.query.filter_by(user_id=user_id).order_by(Watchlist.added_at.desc()).all()
        return jsonify({
            'success': True,
            'watchlist': [item.to_dict() for item in items],
        })
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/watchlist', methods=['POST'])
@require_auth
def add_to_watchlist():
    try:
        user_id = get_user_id()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Support single symbol or list
        symbols = data.get('symbols', [])
        if not symbols and data.get('symbol'):
            symbols = [data['symbol']]
        if not symbols:
            return jsonify({'error': 'symbol or symbols required'}), 400

        added = []
        for sym in symbols:
            sym = sym.upper().strip()
            existing = Watchlist.query.filter_by(user_id=user_id, symbol=sym).first()
            if not existing:
                item = Watchlist(user_id=user_id, symbol=sym)
                db.session.add(item)
                added.append(sym)

        db.session.commit()

        items = Watchlist.query.filter_by(user_id=user_id).order_by(Watchlist.added_at.desc()).all()
        return jsonify({
            'success': True,
            'added': added,
            'watchlist': [item.to_dict() for item in items],
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding to watchlist: {e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/watchlist/<symbol>', methods=['DELETE'])
@require_auth
def remove_from_watchlist(symbol):
    try:
        user_id = get_user_id()
        symbol = symbol.upper().strip()
        item = Watchlist.query.filter_by(user_id=user_id, symbol=symbol).first()
        if not item:
            return jsonify({'error': f'{symbol} not in watchlist'}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True, 'removed': symbol})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing from watchlist: {e}")
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────
# Alerts
# ─────────────────────────────────────

@user_bp.route('/alerts', methods=['GET'])
@require_auth
def get_alerts():
    try:
        user_id = get_user_id()
        query = Alert.query.filter_by(user_id=user_id)

        active_filter = request.args.get('active')
        if active_filter == 'true':
            query = query.filter_by(is_active=True)

        alerts = query.order_by(Alert.created_at.desc()).all()
        return jsonify({
            'success': True,
            'alerts': [a.to_dict() for a in alerts],
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/alerts', methods=['POST'])
@require_auth
def create_alert():
    try:
        user_id = get_user_id()
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        symbol = data.get('symbol', '').upper().strip()
        alert_type = data.get('alert_type', data.get('type', ''))
        condition = data.get('condition', 'above')
        threshold = data.get('threshold')
        recurring = data.get('recurring', False)

        if not symbol or not alert_type or threshold is None:
            return jsonify({'error': 'symbol, alert_type/type, and threshold are required'}), 400

        alert = Alert(
            user_id=user_id,
            symbol=symbol,
            alert_type=alert_type,
            condition=condition,
            threshold=float(threshold),
            recurring=recurring,
        )
        db.session.add(alert)
        db.session.commit()

        return jsonify({
            'success': True,
            'alert': alert.to_dict(),
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating alert: {e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/alerts/<int:alert_id>', methods=['PUT'])
@require_auth
def update_alert(alert_id):
    try:
        user_id = get_user_id()
        alert = Alert.query.filter_by(id=alert_id, user_id=user_id).first()
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404

        data = request.get_json() or {}
        if 'threshold' in data:
            alert.threshold = float(data['threshold'])
        if 'condition' in data:
            alert.condition = data['condition']
        if 'is_active' in data:
            alert.is_active = bool(data['is_active'])
        if 'recurring' in data:
            alert.recurring = bool(data['recurring'])
        if 'alert_type' in data:
            alert.alert_type = data['alert_type']

        db.session.commit()
        return jsonify({'success': True, 'alert': alert.to_dict()})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating alert: {e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/alerts/<int:alert_id>', methods=['DELETE'])
@require_auth
def delete_alert(alert_id):
    try:
        user_id = get_user_id()
        alert = Alert.query.filter_by(id=alert_id, user_id=user_id).first()
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404

        db.session.delete(alert)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting alert: {e}")
        return jsonify({'error': str(e)}), 500


@user_bp.route('/alerts/triggered', methods=['GET'])
@require_auth
def get_triggered_alerts():
    try:
        user_id = get_user_id()
        alerts = Alert.query.filter(
            Alert.user_id == user_id,
            Alert.triggered_at.isnot(None)
        ).order_by(Alert.triggered_at.desc()).limit(50).all()

        return jsonify({
            'success': True,
            'triggered_alerts': [a.to_dict() for a in alerts],
        })
    except Exception as e:
        logger.error(f"Error getting triggered alerts: {e}")
        return jsonify({'error': str(e)}), 500
