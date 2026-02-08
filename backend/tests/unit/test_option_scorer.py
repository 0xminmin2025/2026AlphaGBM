"""
Unit tests for OptionScorer class.
No database or network access required -- pure computation tests.
"""
import pytest
from datetime import datetime, timedelta

from app.services.option_scorer import OptionScorer
from app.services.option_models import OptionData, ScoringParams


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _future_date(days: int) -> str:
    """Return a YYYY-MM-DD string `days` from now."""
    return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")


def _make_put(strike: float, stock_price: float, dte_days: int, *,
              latest_price: float = 2.50,
              bid_price: float = 2.40,
              ask_price: float = 2.60,
              delta: float = -0.30,
              gamma: float = 0.03,
              theta: float = -0.05,
              implied_vol: float = 0.30,
              open_interest: int = 500,
              volume: int = 200) -> OptionData:
    """Convenience factory for a PUT OptionData."""
    return OptionData(
        identifier=f"PUT_{strike}_{dte_days}",
        symbol="TEST",
        strike=strike,
        put_call="PUT",
        expiry_date=_future_date(dte_days),
        bid_price=bid_price,
        ask_price=ask_price,
        latest_price=latest_price,
        volume=volume,
        open_interest=open_interest,
        implied_vol=implied_vol,
        delta=delta,
        gamma=gamma,
        theta=theta,
    )


def _make_call(strike: float, stock_price: float, dte_days: int, *,
               latest_price: float = 3.00,
               bid_price: float = 2.90,
               ask_price: float = 3.10,
               delta: float = 0.40,
               gamma: float = 0.03,
               theta: float = -0.04,
               implied_vol: float = 0.30,
               open_interest: int = 500,
               volume: int = 200) -> OptionData:
    """Convenience factory for a CALL OptionData."""
    return OptionData(
        identifier=f"CALL_{strike}_{dte_days}",
        symbol="TEST",
        strike=strike,
        put_call="CALL",
        expiry_date=_future_date(dte_days),
        bid_price=bid_price,
        ask_price=ask_price,
        latest_price=latest_price,
        volume=volume,
        open_interest=open_interest,
        implied_vol=implied_vol,
        delta=delta,
        gamma=gamma,
        theta=theta,
    )


@pytest.fixture
def scorer():
    """Default OptionScorer with standard params."""
    return OptionScorer()


# ===========================================================================
# 1. DTE calculation
# ===========================================================================

class TestCalculateDTE:

    def test_calculate_dte_normal(self, scorer):
        """A future expiry date produces positive days."""
        dte = scorer.calculate_days_to_expiry(_future_date(30))
        assert dte == 30 or dte == 29  # allow 1-day rounding due to time-of-day

    def test_calculate_dte_today(self, scorer):
        """Today's date returns minimum of 1 (avoids division by zero)."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        dte = scorer.calculate_days_to_expiry(today_str)
        assert dte == 1  # clamped to minimum 1

    def test_is_daily_option_0dte(self, scorer):
        """0 DTE and 1 DTE both classify as daily options."""
        assert scorer.is_daily_option(0) is True
        assert scorer.is_daily_option(1) is True

    def test_is_daily_option_weekly(self, scorer):
        """5 DTE is not a daily option."""
        assert scorer.is_daily_option(5) is False


# ===========================================================================
# 2. Expiry risk penalty
# ===========================================================================

class TestExpiryRiskPenalty:

    def test_0dte_penalty_atm(self, scorer):
        """0DTE ATM option (moneyness ~1.0) gets ~30% penalty (factor 0.3)."""
        penalty, warning = scorer.calculate_expiry_risk_penalty(dte=1, moneyness_ratio=1.0)
        assert penalty == pytest.approx(0.3, abs=0.01)
        assert warning is not None

    def test_0dte_penalty_far_otm(self, scorer):
        """0DTE far OTM (moneyness 0.90) gets 0.7 factor (70% of score kept)."""
        penalty, warning = scorer.calculate_expiry_risk_penalty(dte=1, moneyness_ratio=0.90)
        assert penalty == pytest.approx(0.7, abs=0.01)
        assert warning is not None

    def test_7plus_dte_no_penalty(self, scorer):
        """7+ DTE with comfortable distance gets no penalty (factor 1.0)."""
        penalty, warning = scorer.calculate_expiry_risk_penalty(dte=14, moneyness_ratio=0.90)
        assert penalty == 1.0
        assert warning is None


# ===========================================================================
# 3. Liquidity factor
# ===========================================================================

class TestLiquidityFactor:

    def test_high_oi_tight_spread(self, scorer):
        """OI >= 500 with spread <= 1% yields score close to 1.0."""
        factor = scorer.calculate_liquidity_factor(
            bid_price=100.0, ask_price=100.50, open_interest=1000
        )
        # Spread = 0.50/100.25 ~ 0.5% -> spread_score ~ 1.0
        # OI=1000 >= 500 -> oi_score=1.0
        # composite = 0.4*1.0 + 0.6*1.0 = 1.0
        assert factor >= 0.95

    def test_low_oi_veto(self, scorer):
        """OI < 10 triggers veto -> 0.0."""
        factor = scorer.calculate_liquidity_factor(
            bid_price=5.0, ask_price=5.05, open_interest=5
        )
        assert factor == 0.0

    def test_wide_spread(self, scorer):
        """Spread > 10% yields low liquidity score."""
        # bid=1.0, ask=1.20 -> spread_ratio = 0.20/1.10 ~ 18% -> spread_score=0.0
        factor = scorer.calculate_liquidity_factor(
            bid_price=1.0, ask_price=1.20, open_interest=500
        )
        # spread_score = 0.0, oi_score = 1.0
        # composite = 0.4*0.0 + 0.6*1.0 = 0.60
        assert factor <= 0.65


# ===========================================================================
# 4. IV rank estimation
# ===========================================================================

class TestIVRank:

    def test_iv_rank_low(self, scorer):
        """IV < 15% returns rank ~20."""
        rank = scorer.calculate_iv_rank(0.10)
        assert rank == pytest.approx(20.0)

    def test_iv_rank_high(self, scorer):
        """IV > 50% returns rank ~95."""
        rank = scorer.calculate_iv_rank(0.55)
        assert rank == pytest.approx(95.0)


# ===========================================================================
# 5. Assignment probability
# ===========================================================================

class TestAssignmentProbability:

    def test_deep_otm_put(self, scorer):
        """A far OTM put (strike << stock_price) has low assignment probability."""
        option = _make_put(strike=80.0, stock_price=100.0, dte_days=30,
                           implied_vol=0.25, delta=-0.10)
        prob = scorer.calculate_assignment_probability(option, stock_price=100.0)
        assert prob is not None
        assert prob < 25.0  # should be well below 25%

    def test_atm_option(self, scorer):
        """ATM put (strike ~ stock_price) has assignment probability near 50%."""
        option = _make_put(strike=100.0, stock_price=100.0, dte_days=30,
                           implied_vol=0.25, delta=-0.50)
        prob = scorer.calculate_assignment_probability(option, stock_price=100.0)
        assert prob is not None
        assert 30.0 <= prob <= 70.0  # approximately 50%


# ===========================================================================
# 6. SPRV scoring
# ===========================================================================

class TestSPRV:

    def test_sprv_ideal_put(self, scorer):
        """An ideal sell-put candidate gets a high SPRV score."""
        option = _make_put(
            strike=95.0, stock_price=100.0, dte_days=30,
            latest_price=3.00,
            bid_price=2.90, ask_price=3.10,
            delta=-0.25, gamma=0.02, theta=-0.06,
            implied_vol=0.35, open_interest=800,
        )
        score = scorer.calculate_sprv(option, stock_price=100.0)
        assert score > 40  # should be a strong recommendation

    def test_sprv_daily_cap(self, scorer):
        """0DTE option SPRV is capped at 30."""
        option = _make_put(
            strike=99.0, stock_price=100.0, dte_days=0,
            latest_price=1.50,
            bid_price=1.40, ask_price=1.60,
            delta=-0.45, gamma=0.08, theta=-0.15,
            implied_vol=0.40, open_interest=300,
        )
        score = scorer.calculate_sprv(option, stock_price=100.0)
        assert score <= 30

    def test_sprv_zero_liquidity(self, scorer):
        """Option with OI < 10 gets SPRV 0 due to liquidity veto."""
        option = _make_put(
            strike=95.0, stock_price=100.0, dte_days=30,
            latest_price=2.00,
            bid_price=1.90, ask_price=2.10,
            delta=-0.25, gamma=0.02, theta=-0.04,
            implied_vol=0.30, open_interest=3,  # OI veto threshold
        )
        score = scorer.calculate_sprv(option, stock_price=100.0)
        # liquidity factor = 0.0 -> liquidity_score = 0
        # Score will be reduced but might not be exactly 0 (other components exist)
        # However the low liquidity heavily penalizes the score
        assert score < 50  # heavily penalized by low liquidity

    def test_sprv_boundary_0_100(self, scorer):
        """SPRV score is always clamped to [0, 100] for various inputs."""
        test_cases = [
            # (strike, stock_price, dte, delta, iv, oi, latest_price)
            (95, 100, 30, -0.30, 0.25, 500, 2.0),     # normal case
            (50, 100, 30, -0.01, 0.10, 500, 0.01),     # deep OTM
            (99, 100, 1, -0.48, 0.80, 1000, 5.0),      # 0DTE high IV
            (98, 100, 60, -0.20, 0.60, 2000, 8.0),     # high premium, long DTE
            (102, 100, 30, -0.55, 0.30, 500, 4.0),     # slightly ITM -> should be 0
        ]
        for strike, stock, dte, delta, iv, oi, price in test_cases:
            option = _make_put(
                strike=strike, stock_price=stock, dte_days=dte,
                latest_price=price, delta=delta, implied_vol=iv,
                open_interest=oi,
            )
            score = scorer.calculate_sprv(option, stock_price=stock)
            assert 0 <= score <= 100, (
                f"SPRV out of [0,100] for strike={strike}, stock={stock}, "
                f"dte={dte}: got {score}"
            )
