"""
Unit tests for the Feishu (Lark) bot webhook service.

Tests get_daily_stats, build_card_message, and send_daily_report
with mocked database queries and HTTP requests.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stats(**overrides):
    """Return a sample stats dict matching get_daily_stats output."""
    base = {
        'date': '2026-02-08',
        'new_users_today': 15,
        'total_users': 1200,
        'new_paid_today': 3,
        'total_paid_users': 85,
        'today_revenue': 29.97,
        'total_revenue': 12345.67,
    }
    base.update(overrides)
    return base


# ===================================================================
# test_get_daily_stats
# ===================================================================

class TestGetDailyStats:
    """get_daily_stats should return a stats dict with required keys."""

    @patch('app.services.feishu_bot.db')
    @patch('app.services.feishu_bot.Transaction')
    @patch('app.services.feishu_bot.Subscription')
    @patch('app.services.feishu_bot.User')
    def test_returns_stats_dict(self, MockUser, MockSub, MockTx, mock_db):
        from app.services.feishu_bot import get_daily_stats

        # Make SQLAlchemy column-style comparison operators work on mock attrs
        # so that expressions like `User.created_at >= datetime(...)` don't raise
        col_mock = MagicMock()
        col_mock.__ge__ = MagicMock(return_value=MagicMock())
        col_mock.__le__ = MagicMock(return_value=MagicMock())
        MockUser.created_at = col_mock

        sub_col = MagicMock()
        sub_col.__ge__ = MagicMock(return_value=MagicMock())
        sub_col.__le__ = MagicMock(return_value=MagicMock())
        sub_col.__eq__ = MagicMock(return_value=MagicMock())
        MockSub.created_at = sub_col
        MockSub.status = MagicMock()
        MockSub.status.__eq__ = MagicMock(return_value=MagicMock())

        tx_col = MagicMock()
        tx_col.__ge__ = MagicMock(return_value=MagicMock())
        tx_col.__le__ = MagicMock(return_value=MagicMock())
        tx_col.__eq__ = MagicMock(return_value=MagicMock())
        MockTx.created_at = tx_col
        MockTx.status = MagicMock()
        MockTx.status.__eq__ = MagicMock(return_value=MagicMock())
        MockTx.amount = MagicMock()

        # Mock User.query
        MockUser.query.filter.return_value.count.return_value = 10
        MockUser.query.count.return_value = 500

        # Mock Subscription.query
        MockSub.query.filter.return_value.count.return_value = 2
        MockSub.user_id = MagicMock()

        # Mock distinct paid users and revenue queries
        mock_db.session.query.return_value.filter.return_value.scalar.return_value = 40

        stats = get_daily_stats()

        assert isinstance(stats, dict)
        assert 'date' in stats
        assert 'new_users_today' in stats
        assert 'total_users' in stats
        assert 'new_paid_today' in stats
        assert 'total_paid_users' in stats
        assert 'today_revenue' in stats
        assert 'total_revenue' in stats


# ===================================================================
# test_build_card_message
# ===================================================================

class TestBuildCardMessage:
    """build_card_message should return a valid Feishu card format."""

    def test_returns_valid_card(self):
        from app.services.feishu_bot import build_card_message

        stats = _make_stats()
        msg = build_card_message(stats)

        assert msg['msg_type'] == 'interactive'
        assert 'card' in msg
        assert 'header' in msg['card']
        assert 'elements' in msg['card']
        assert msg['card']['header']['template'] == 'blue'

    def test_card_contains_date(self):
        from app.services.feishu_bot import build_card_message

        stats = _make_stats(date='2026-02-08')
        msg = build_card_message(stats)

        # The date should appear somewhere in the card elements
        card_str = str(msg)
        assert '2026-02-08' in card_str

    def test_card_contains_revenue(self):
        from app.services.feishu_bot import build_card_message

        stats = _make_stats(today_revenue=99.99)
        msg = build_card_message(stats)

        card_str = str(msg)
        assert '99.99' in card_str

    def test_card_has_elements(self):
        from app.services.feishu_bot import build_card_message

        stats = _make_stats()
        msg = build_card_message(stats)

        elements = msg['card']['elements']
        # Should have date, hr, users, hr, paid, hr, revenue = at least 7
        assert len(elements) >= 7


# ===================================================================
# test_send_report_success
# ===================================================================

class TestSendReportSuccess:
    """Successful POST to webhook should return True."""

    @patch('app.services.feishu_bot.get_daily_stats')
    @patch('app.services.feishu_bot.requests.post')
    @patch.dict('os.environ', {'FEISHU_WEBHOOK_URL': 'https://open.feishu.cn/open-apis/bot/v2/hook/test123'})
    def test_returns_true_on_success(self, mock_post, mock_stats):
        from app.services.feishu_bot import send_daily_report

        mock_stats.return_value = _make_stats()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {'code': 0, 'msg': 'success'}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = send_daily_report()

        assert result is True
        mock_post.assert_called_once()

    @patch('app.services.feishu_bot.get_daily_stats')
    @patch('app.services.feishu_bot.requests.post')
    @patch.dict('os.environ', {'FEISHU_WEBHOOK_URL': 'https://open.feishu.cn/open-apis/bot/v2/hook/test123'})
    def test_returns_false_on_api_error(self, mock_post, mock_stats):
        from app.services.feishu_bot import send_daily_report

        mock_stats.return_value = _make_stats()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {'code': 9499, 'msg': 'bad request'}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        result = send_daily_report()
        assert result is False


# ===================================================================
# test_send_report_no_webhook
# ===================================================================

class TestSendReportNoWebhook:
    """When FEISHU_WEBHOOK_URL is not set, send_daily_report returns False."""

    @patch('app.services.feishu_bot.FEISHU_WEBHOOK_URL', '')
    @patch.dict('os.environ', {'FEISHU_WEBHOOK_URL': ''})
    def test_returns_false_without_url(self):
        from app.services.feishu_bot import send_daily_report

        result = send_daily_report()
        assert result is False
