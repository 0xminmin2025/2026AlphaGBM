"""API Key管理路由"""

from flask import Blueprint, jsonify, request, g
from ..models import db, ApiKey
from ..utils.auth import require_auth

apikey_bp = Blueprint('apikey', __name__, url_prefix='/api/keys')


@apikey_bp.route('', methods=['GET'])
@require_auth
def list_keys():
    """列出用户所有API Key（只返回前缀，不返回完整key）"""
    keys = ApiKey.query.filter_by(user_id=g.user_id).all()
    return jsonify({
        'keys': [{
            'id': k.id,
            'name': k.name,
            'prefix': k.key_prefix,
            'is_active': k.is_active,
            'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
            'created_at': k.created_at.isoformat()
        } for k in keys]
    })


@apikey_bp.route('', methods=['POST'])
@require_auth
def create_key():
    """创建新API Key。完整key只在创建时返回一次"""
    data = request.get_json() or {}
    name = data.get('name', 'Default')

    # 限制每用户最多5个key
    existing_count = ApiKey.query.filter_by(user_id=g.user_id).count()
    if existing_count >= 5:
        return jsonify({'error': '最多创建5个API Key'}), 400

    raw_key = ApiKey.generate_key()

    new_key = ApiKey(
        user_id=g.user_id,
        key_hash=ApiKey.hash_key(raw_key),
        key_prefix=raw_key[:13],
        name=name
    )
    db.session.add(new_key)
    db.session.commit()

    return jsonify({
        'id': new_key.id,
        'key': raw_key,
        'name': new_key.name,
        'prefix': new_key.key_prefix,
        'message': '请立即保存此API Key，关闭后将无法再次查看完整内容'
    }), 201


@apikey_bp.route('/<int:key_id>', methods=['DELETE'])
@require_auth
def delete_key(key_id):
    """删除API Key"""
    key = ApiKey.query.filter_by(id=key_id, user_id=g.user_id).first()
    if not key:
        return jsonify({'error': 'Key not found'}), 404

    db.session.delete(key)
    db.session.commit()
    return jsonify({'message': 'API Key已删除'})


@apikey_bp.route('/<int:key_id>/toggle', methods=['POST'])
@require_auth
def toggle_key(key_id):
    """启用/停用API Key"""
    key = ApiKey.query.filter_by(id=key_id, user_id=g.user_id).first()
    if not key:
        return jsonify({'error': 'Key not found'}), 404

    key.is_active = not key.is_active
    db.session.commit()
    return jsonify({
        'id': key.id,
        'is_active': key.is_active,
        'message': f"API Key已{'启用' if key.is_active else '停用'}"
    })
