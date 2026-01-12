"""
Options Module API Endpoints
Ported from new_options_module/routes.py
"""

from flask import Blueprint, jsonify, request
from ..services.options_service import OptionsService
from ..models import ServiceType
# Attempt to import check_quota. If circular import risk, use local import inside function but decorator needs it.
# decorators.py imports PaymentService, which imports models. 
# options.py imports OptionsService, which imports models.
# Should be fine.
from ..utils.decorators import check_quota
from ..utils.auth import require_auth

options_bp = Blueprint('options', __name__, url_prefix='/api/options')

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

@options_bp.route('/chain/<symbol>/<expiry_date>', methods=['GET'])
@check_quota(ServiceType.OPTION_ANALYSIS.value, amount=1) 
def get_option_chain(symbol, expiry_date):
    """Get option chain with scoring"""
    try:
        response = OptionsService.get_option_chain(symbol, expiry_date)
        return jsonify(response.dict()), 200
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

@options_bp.route('/enhanced-analysis/<symbol>/<path:option_identifier>', methods=['GET'])
@check_quota(ServiceType.DEEP_REPORT.value, amount=1) # Or maybe just option analysis?
# Enhanced analysis implies more compute. Let's use DEEP_REPORT or just standard OPTION_ANALYSIS.
# Given it's "enhanced", maybe DEEP_REPORT. But user might not have credits for it if it's 0 free quota.
# Let's stick to OPTION_ANALYSIS for now or just free if it's part of the flow.
# Actually, let's use OPTION_ANALYSIS but maybe higher amount?
# Simplify: Use OPTION_ANALYSIS.
def get_enhanced_analysis(symbol, option_identifier):
    """Get enhanced analysis (VRP, Risk)"""
    try:
        response = OptionsService.get_enhanced_analysis(symbol, option_identifier)
        return jsonify(response.dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
