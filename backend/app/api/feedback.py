from flask import Blueprint, request, jsonify, g
from ..models import db, Feedback
from ..utils.auth import require_auth
import logging
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__, url_prefix='/api/feedback')
logger = logging.getLogger(__name__)

@feedback_bp.route('', methods=['POST'])
@require_auth
def submit_feedback():
    """
    Submit user feedback
    Body: {
        "type": "bug|suggestion|question",
        "content": "feedback text",
        "ticker": "optional ticker"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        feedback_type = data.get('type', 'general')
        content = data.get('content', '').strip()
        ticker = data.get('ticker')
        
        if not content:
            return jsonify({'success': False, 'error': 'Feedback content is required'}), 400
        
        # Validate feedback type
        valid_types = ['bug', 'suggestion', 'question', 'general']
        if feedback_type not in valid_types:
            feedback_type = 'general'
        
        # Get user ID from Flask global (set by require_auth)
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        # Get IP address
        ip_address = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        # Create feedback record
        feedback = Feedback(
            user_id=user_id,
            type=feedback_type,
            content=content,
            ticker=ticker,
            ip_address=ip_address,
            submitted_at=datetime.utcnow()
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        logger.info(f"Feedback submitted by user {user_id}: type={feedback_type}, ticker={ticker}")
        
        return jsonify({
            'success': True,
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting feedback: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
