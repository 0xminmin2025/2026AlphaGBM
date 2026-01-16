from flask import Blueprint, jsonify
from ..utils.auth import require_auth, get_current_user_info
from ..models import User, db

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

@user_bp.route('/profile', methods=['GET'])
@require_auth
def get_profile():
    return jsonify({'message': 'User Profile Endpoint'})
