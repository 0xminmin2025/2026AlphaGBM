"""
Integration tests for the portfolio API endpoints.

Endpoints tested:
    GET /api/portfolio/holdings
    GET /api/portfolio/daily-stats
"""
import pytest
from unittest.mock import patch, MagicMock


class TestPortfolioHoldings:
    """Tests for the portfolio holdings endpoint (no auth required)."""

    def test_holdings(self, client):
        """GET /api/portfolio/holdings should return 200 with holdings data."""
        # Mock DataProvider and exchange rates so no real network calls happen
        with patch(
            'app.api.portfolio.DataProvider'
        ) as mock_dp, patch(
            'app.api.portfolio.get_exchange_rates',
            return_value={'USD': 1.0, 'HKD': 0.128, 'CNY': 0.137},
        ), patch(
            'app.api.portfolio.convert_to_usd',
            side_effect=lambda amt, cur, rates: amt,
        ):
            mock_ticker_obj = MagicMock()
            mock_ticker_obj.info = {
                'currentPrice': 195.0,
                'regularMarketPrice': 195.0,
            }
            mock_dp.return_value = mock_ticker_obj

            resp = client.get('/api/portfolio/holdings')

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'data' in data
        # Even with no DB rows the endpoint returns the structure
        holdings_data = data['data']
        assert 'holdings_by_style' in holdings_data
        assert 'style_stats' in holdings_data


class TestPortfolioDailyStats:
    """Tests for the daily portfolio stats endpoint (no auth required)."""

    def test_daily_stats(self, client):
        """GET /api/portfolio/daily-stats should return 200."""
        resp = client.get('/api/portfolio/daily-stats')

        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'data' in data
        stats = data['data']
        assert 'total_investment' in stats
        assert 'total_market_value' in stats
        assert 'total_profit_loss' in stats
        assert 'total_profit_loss_percent' in stats
