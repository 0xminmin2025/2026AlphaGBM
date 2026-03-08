"""
叙事雷达 API 路由 - Narrative Radar API Routes
"""

from flask import Blueprint, request, jsonify
from app.services.narrative_service import analyze_narrative, get_preset_narratives

narrative_bp = Blueprint('narrative', __name__, url_prefix='/api/narrative')


@narrative_bp.route('/presets', methods=['GET'])
def get_presets():
    """
    获取所有预设叙事

    Returns:
        JSON: 按类型分组的预设叙事列表
        {
            "person": [...],
            "institution": [...],
            "theme": [...]
        }
    """
    presets = get_preset_narratives()
    # 按类型分组
    grouped = {
        'person': [],
        'institution': [],
        'theme': []
    }
    for key, value in presets.items():
        item = value.copy()
        item['key'] = key
        grouped[value['type']].append(item)

    return jsonify(grouped)


@narrative_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    分析叙事相关股票

    Request Body:
        {
            "concept": "用户自定义概念（可选）",
            "narrative_key": "预设叙事key（可选）",
            "market": "US/HK/CN（可选，默认US）",
            "lang": "zh/en（可选，默认zh）"
        }

    Returns:
        JSON: 叙事分析结果，包含股票列表和期权策略
    """
    data = request.get_json()
    concept = data.get('concept', '')
    market = data.get('market', 'US')
    narrative_key = data.get('narrative_key')
    lang = data.get('lang', 'zh')  # 语言参数，默认中文

    if not concept and not narrative_key:
        return jsonify({'error': 'Concept or narrative_key is required'}), 400

    result = analyze_narrative(concept, market, narrative_key, lang)
    return jsonify(result)
