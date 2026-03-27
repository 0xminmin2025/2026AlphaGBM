"""
Integration tests for agent-friendly sync endpoints.

Endpoints tested:
    POST /api/stock/analyze-sync
    GET  /api/stock/quick-quote/<ticker>
    POST /api/options/chain-sync
    POST /api/options/enhanced-sync
    GET  /api/options/snapshot/<symbol>
    GET  /api/docs/  (SKILL.md)
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import date


# Mock payment to always allow
MOCK_PAYMENT = patch(
    'app.services.payment_service.PaymentService.check_and_deduct_credits',
    return_value=(True, 'OK', 999, {'is_free': True, 'free_remaining': 2, 'free_quota': 3, 'free_used': 1}),
)


# ---------------------------------------------------------------------------
# POST /api/stock/analyze-sync
# ---------------------------------------------------------------------------

class TestStockAnalyzeSync:

    def test_requires_auth(self, client):
        resp = client.post('/api/stock/analyze-sync', json={'ticker': 'AAPL'})
        assert resp.status_code == 401

    def test_missing_ticker(self, client, auth_headers, mock_supabase_auth, sample_user):
        with MOCK_PAYMENT:
            resp = client.post(
                '/api/stock/analyze-sync',
                json={},
                headers=auth_headers,
            )
        assert resp.status_code == 400

    def test_cache_hit_returns_result(self, client, auth_headers, mock_supabase_auth, sample_user):
        """When daily cache exists, analyze-sync returns it directly."""
        mock_cache = MagicMock()
        mock_cache.full_analysis_data = {
            'success': True,
            'data': {'symbol': 'AAPL', 'price': 185.5, 'ev_model': {}},
            'risk': {'score': 3, 'level': 'medium'},
            'report': 'Test report'
        }

        with MOCK_PAYMENT, patch('app.api.stock.get_cached_analysis', return_value=mock_cache):
            resp = client.post(
                '/api/stock/analyze-sync',
                json={'ticker': 'AAPL', 'style': 'quality'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['data']['symbol'] == 'AAPL'

    def test_compact_mode(self, client, auth_headers, mock_supabase_auth, sample_user):
        """?compact=true returns condensed response."""
        mock_cache = MagicMock()
        mock_cache.full_analysis_data = {
            'success': True,
            'data': {
                'symbol': 'AAPL', 'price': 185.5,
                'ev_model': {'ev_score': 7.1, 'recommendation': {'action': 'BUY', 'confidence': 'high'}}
            },
            'risk': {'score': 3.2, 'level': 'medium', 'suggested_position': 15},
            'report': '# Report\nApple looks strong.'
        }

        with MOCK_PAYMENT, patch('app.api.stock.get_cached_analysis', return_value=mock_cache):
            resp = client.post(
                '/api/stock/analyze-sync?compact=true',
                json={'ticker': 'AAPL'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'ticker' in data
        assert 'recommendation' in data
        assert 'ai_summary' in data
        assert 'key_metrics' in data
        # Compact should NOT have 'data' wrapper
        assert 'data' not in data or data.get('data') is None

    def test_cache_miss_runs_analysis(self, client, auth_headers, mock_supabase_auth, sample_user):
        """When no cache, runs full analysis synchronously."""
        mock_result = {
            'success': True,
            'data': {'symbol': 'TSLA', 'price': 248.5, 'ev_model': {}},
            'risk': {'score': 4, 'level': 'medium'},
            'report': 'TSLA report'
        }

        with MOCK_PAYMENT, \
             patch('app.api.stock.get_cached_analysis', return_value=None), \
             patch('app.api.stock.get_stock_analysis_data', return_value=mock_result), \
             patch('app.api.stock.convert_numpy_types', side_effect=lambda x: x), \
             patch('app.api.stock.db'):
            resp = client.post(
                '/api/stock/analyze-sync',
                json={'ticker': 'TSLA', 'style': 'balanced'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True


# ---------------------------------------------------------------------------
# GET /api/stock/quick-quote/<ticker>
# ---------------------------------------------------------------------------

class TestQuickQuote:

    def test_requires_auth(self, client):
        resp = client.get('/api/stock/quick-quote/AAPL')
        assert resp.status_code == 401

    def test_returns_quote(self, client, auth_headers, mock_supabase_auth, sample_user):
        mock_info = {
            'currentPrice': 185.5,
            'previousClose': 183.0,
            'currency': 'USD',
            'volume': 45000000,
            'marketCap': 2800000000000,
            'trailingPE': 28.5,
            'forwardPE': 26.1,
            'fiftyTwoWeekHigh': 199.6,
            'fiftyTwoWeekLow': 164.1,
            'sector': 'Technology',
            'shortName': 'Apple Inc.',
        }

        with patch('app.api.stock.DataProvider') as MockDP:
            MockDP.return_value.info = mock_info
            resp = client.get('/api/stock/quick-quote/AAPL', headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['ticker'] == 'AAPL'
        assert data['price'] == 185.5
        assert data['pe_ratio'] == 28.5
        assert data['name'] == 'Apple Inc.'

    def test_unknown_ticker(self, client, auth_headers, mock_supabase_auth, sample_user):
        with patch('app.api.stock.DataProvider') as MockDP:
            MockDP.return_value.info = {}
            resp = client.get('/api/stock/quick-quote/ZZZZZ', headers=auth_headers)

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/options/chain-sync
# ---------------------------------------------------------------------------

class TestOptionsChainSync:

    def test_requires_auth(self, client):
        resp = client.post('/api/options/chain-sync', json={'symbol': 'AAPL', 'expiry_date': '2026-04-17'})
        assert resp.status_code == 401

    def test_missing_params(self, client, auth_headers, mock_supabase_auth, sample_user):
        with MOCK_PAYMENT:
            resp = client.post(
                '/api/options/chain-sync',
                json={'symbol': 'AAPL'},  # missing expiry_date
                headers=auth_headers,
            )
        assert resp.status_code == 400

    def test_returns_chain(self, client, auth_headers, mock_supabase_auth, sample_user):
        mock_result = {
            'symbol': 'AAPL', 'real_stock_price': 185.5, 'expiry_date': '2026-04-17',
            'iv_rank_30d': 45.2, 'calls': [], 'puts': [],
            'summary': {'best_strategies': [], 'overall_recommendation': {}}
        }

        with MOCK_PAYMENT, \
             patch('app.api.options.get_options_analysis_data', return_value=mock_result):
            resp = client.post(
                '/api/options/chain-sync',
                json={'symbol': 'AAPL', 'expiry_date': '2026-04-17'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['symbol'] == 'AAPL'

    def test_compact_mode(self, client, auth_headers, mock_supabase_auth, sample_user):
        mock_result = {
            'symbol': 'AAPL', 'real_stock_price': 185.5, 'expiry_date': '2026-04-17',
            'iv_rank_30d': 45.2, 'iv_percentile_30d': 42, 'historical_volatility': 0.25,
            'calls': [{'strike': 185, 'score': 72, 'bid': 5.0, 'ask': 5.5, 'impliedVolatility': 0.28, 'volume': 100, 'openInterest': 500, 'delta': 0.52}],
            'puts': [],
            'summary': {'best_strategies': [], 'overall_recommendation': {}}
        }

        with MOCK_PAYMENT, \
             patch('app.api.options.get_options_analysis_data', return_value=mock_result):
            resp = client.post(
                '/api/options/chain-sync?compact=true',
                json={'symbol': 'AAPL', 'expiry_date': '2026-04-17'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert 'top_calls' in data
        assert 'iv_rank' in data


# ---------------------------------------------------------------------------
# POST /api/options/enhanced-sync
# ---------------------------------------------------------------------------

class TestOptionsEnhancedSync:

    def test_requires_auth(self, client):
        resp = client.post('/api/options/enhanced-sync', json={'symbol': 'AAPL', 'option_identifier': 'X'})
        assert resp.status_code == 401

    def test_returns_enhanced(self, client, auth_headers, mock_supabase_auth, sample_user):
        mock_result = {
            'symbol': 'AAPL', 'option_identifier': 'AAPL260417C00190000',
            'vrp_analysis': {'iv': 0.28, 'historical_volatility': 0.25, 'vrp': 0.03},
            'risk_analysis': {'greeks': {'delta': 0.65, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.18}, 'overall_risk': 'medium'}
        }

        with MOCK_PAYMENT, \
             patch('app.api.options.get_options_analysis_data', return_value=mock_result):
            resp = client.post(
                '/api/options/enhanced-sync',
                json={'symbol': 'AAPL', 'option_identifier': 'AAPL260417C00190000'},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['symbol'] == 'AAPL'
        assert 'vrp_analysis' in data


# ---------------------------------------------------------------------------
# GET /api/options/snapshot/<symbol>
# ---------------------------------------------------------------------------

class TestOptionsSnapshot:

    def test_requires_auth(self, client):
        resp = client.get('/api/options/snapshot/AAPL')
        assert resp.status_code == 401

    def test_returns_snapshot(self, client, auth_headers, mock_supabase_auth, sample_user):
        # Mock expirations
        mock_exp = MagicMock()
        mock_exp.expirations = ['2026-04-17', '2026-05-15']

        # Mock chain
        mock_chain = MagicMock()
        mock_chain.dict.return_value = {
            'iv_rank_30d': 72.3,
            'iv_percentile_30d': 68.5,
            'historical_volatility': 0.45,
            'real_stock_price': 142.5,
            'calls': [
                {'strike': 140, 'impliedVolatility': 0.50, 'volume': 100},
                {'strike': 145, 'impliedVolatility': 0.55, 'volume': 80},
            ],
            'puts': [],
        }

        # Mock quote
        mock_quote = MagicMock()
        mock_quote.current_price = 142.5

        with patch.object(OptionsService, 'get_expirations', return_value=mock_exp), \
             patch.object(OptionsService, 'get_option_chain', return_value=mock_chain), \
             patch.object(OptionsService, 'get_stock_quote', return_value=mock_quote):
            resp = client.get('/api/options/snapshot/NVDA', headers=auth_headers)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['symbol'] == 'NVDA'
        assert data['iv_rank'] == 72.3
        assert data['hv_30d'] == 0.45
        assert data['vrp'] is not None
        assert data['vrp_level'] is not None


# ---------------------------------------------------------------------------
# GET /api/docs/  (SKILL.md)
# ---------------------------------------------------------------------------

class TestSkillMd:

    def test_serves_skill_md(self, client):
        """SKILL.md should be publicly accessible as plain text."""
        resp = client.get('/api/docs/')
        assert resp.status_code == 200
        assert 'text/plain' in resp.content_type
        text = resp.data.decode('utf-8')
        # Verify new endpoints are documented
        assert '/stock/analyze-sync' in text
        assert '/stock/quick-quote' in text
        assert '/options/chain-sync' in text
        assert '/options/enhanced-sync' in text
        assert '/options/snapshot' in text
        assert '/options/tools/scan' in text
        assert '/options/tools/strategy/build' in text
        assert 'compact=true' in text


# Need to import OptionsService for patching
from app.services.options_service import OptionsService
