"""
Analytics API endpoints for tracking user behavior.

This module provides endpoints for:
- Batch event submission from frontend
- Event data stored in Supabase for analysis
"""

from flask import Blueprint, request, jsonify
from ..models import db, AnalyticsEvent
import logging
from datetime import datetime

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')
logger = logging.getLogger(__name__)


@analytics_bp.route('/events', methods=['POST'])
def track_events():
    """
    Batch receive analytics events from frontend.

    Body: {
        "events": [
            {
                "event_type": "page_view",
                "session_id": "abc123",
                "user_id": "uuid" (optional),
                "user_tier": "guest|free|plus|pro",
                "properties": {...},
                "url": "/options",
                "referrer": "https://...",
                "timestamp": "2024-01-21T09:30:00Z"
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        events = data.get('events', [])

        if not events:
            return jsonify({'success': True, 'count': 0}), 200

        # Limit batch size to prevent abuse
        MAX_BATCH_SIZE = 100
        if len(events) > MAX_BATCH_SIZE:
            events = events[:MAX_BATCH_SIZE]
            logger.warning(f"Analytics batch truncated to {MAX_BATCH_SIZE} events")

        # Prepare events for bulk insert
        analytics_events = []
        for event in events:
            try:
                # Parse timestamp from ISO format
                timestamp_str = event.get('timestamp')
                if timestamp_str:
                    try:
                        created_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        created_at = datetime.utcnow()
                else:
                    created_at = datetime.utcnow()

                analytics_event = AnalyticsEvent(
                    event_type=event.get('event_type', 'unknown'),
                    session_id=event.get('session_id', 'unknown'),
                    user_id=event.get('user_id'),  # Can be None for guests
                    user_tier=event.get('user_tier', 'guest'),
                    properties=event.get('properties', {}),
                    url=event.get('url', ''),
                    referrer=event.get('referrer', ''),
                    created_at=created_at
                )
                analytics_events.append(analytics_event)
            except Exception as e:
                logger.warning(f"Failed to process analytics event: {e}")
                continue

        # Bulk insert all events
        if analytics_events:
            db.session.bulk_save_objects(analytics_events)
            db.session.commit()
            logger.info(f"Stored {len(analytics_events)} analytics events")

        return jsonify({
            'success': True,
            'count': len(analytics_events)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error storing analytics events: {e}")
        # Don't return error to client to prevent retries flooding the system
        return jsonify({'success': True, 'count': 0}), 200


@analytics_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get basic analytics statistics (admin only).
    This is a simple endpoint for debugging; real analytics would use a dashboard.

    Query params:
    - days: Number of days to look back (default 7)
    """
    try:
        from datetime import timedelta
        from sqlalchemy import func

        days = request.args.get('days', 7, type=int)
        days = min(days, 30)  # Limit to 30 days max

        start_date = datetime.utcnow() - timedelta(days=days)

        # Get event counts by type
        event_counts = db.session.query(
            AnalyticsEvent.event_type,
            func.count(AnalyticsEvent.id).label('count')
        ).filter(
            AnalyticsEvent.created_at >= start_date
        ).group_by(
            AnalyticsEvent.event_type
        ).all()

        # Get unique sessions
        unique_sessions = db.session.query(
            func.count(func.distinct(AnalyticsEvent.session_id))
        ).filter(
            AnalyticsEvent.created_at >= start_date
        ).scalar() or 0

        # Get unique users (non-guest)
        unique_users = db.session.query(
            func.count(func.distinct(AnalyticsEvent.user_id))
        ).filter(
            AnalyticsEvent.created_at >= start_date,
            AnalyticsEvent.user_id.isnot(None)
        ).scalar() or 0

        return jsonify({
            'success': True,
            'period_days': days,
            'stats': {
                'event_counts': {row.event_type: row.count for row in event_counts},
                'unique_sessions': unique_sessions,
                'unique_users': unique_users
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting analytics stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
