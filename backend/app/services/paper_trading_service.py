"""
Paper Trading Service - Internal paper trading simulator

Records simulated trades, tracks virtual positions, and computes daily
NAV/P&L snapshots using real market prices via DataProvider.
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional

from ..models import db, PaperTrade, PaperPosition, PaperPerformance
from .data_provider import DataProvider

logger = logging.getLogger(__name__)

INITIAL_CAPITAL = 100_000.0  # $100K starting capital


class PaperTradingService:
    """Paper trading engine for simulated strategy execution."""

    def execute_trade(self, ticker: str, action: str, quantity: int, price: float,
                      strategy: str, security_type: str = 'STOCK',
                      expiry: str = None, strike: float = None,
                      option_right: str = None, stop_loss: float = None,
                      notes: str = None) -> Dict[str, Any]:
        """
        Execute a paper trade and update positions.

        For SELL on options (selling to open), quantity is stored as negative.
        For BUY to close a short option, it reduces the negative position.
        """
        try:
            # Record the trade
            trade = PaperTrade(
                ticker=ticker,
                security_type=security_type,
                action=action,
                quantity=quantity,
                price=price,
                strategy=strategy,
                status='filled',
                expiry=expiry,
                strike=strike,
                option_right=option_right,
                stop_loss=stop_loss,
                notes=notes,
            )
            db.session.add(trade)

            # Update position
            self._update_position(ticker, action, quantity, price, strategy,
                                  security_type, expiry, strike, option_right, stop_loss)

            db.session.commit()
            logger.info(f"Paper trade executed: {action} {quantity} {ticker} @ {price} [{strategy}]")
            return {'success': True, 'trade': trade.to_dict()}

        except Exception as e:
            db.session.rollback()
            logger.error(f"Paper trade failed: {e}")
            return {'success': False, 'error': str(e)}

    def _update_position(self, ticker: str, action: str, quantity: int, price: float,
                         strategy: str, security_type: str, expiry: str = None,
                         strike: float = None, option_right: str = None,
                         stop_loss: float = None):
        """Update or create position based on trade."""
        # Find existing position
        query = PaperPosition.query.filter_by(
            ticker=ticker, strategy=strategy, security_type=security_type
        )
        if security_type == 'OPTION':
            query = query.filter_by(expiry=expiry, strike=strike, option_right=option_right)

        position = query.first()

        if action == 'BUY':
            signed_qty = quantity
        else:  # SELL
            signed_qty = -quantity

        if position:
            old_qty = position.quantity
            new_qty = old_qty + signed_qty

            if new_qty == 0:
                # Position closed - calculate realized P&L
                realized_pnl = (price - position.avg_cost) * old_qty
                # Record P&L on the closing trade
                latest_trade = PaperTrade.query.filter_by(
                    ticker=ticker, strategy=strategy
                ).order_by(PaperTrade.id.desc()).first()
                if latest_trade:
                    latest_trade.pnl = realized_pnl

                db.session.delete(position)
            else:
                # Adjust position
                if (action == 'BUY' and old_qty > 0) or (action == 'SELL' and old_qty < 0):
                    # Adding to position - update avg cost
                    total_cost = position.avg_cost * abs(old_qty) + price * quantity
                    position.avg_cost = total_cost / abs(new_qty)
                position.quantity = new_qty
                if stop_loss:
                    position.stop_loss = stop_loss
                position.updated_at = datetime.utcnow()
        else:
            # New position
            position = PaperPosition(
                ticker=ticker,
                security_type=security_type,
                strategy=strategy,
                quantity=signed_qty,
                avg_cost=price,
                expiry=expiry,
                strike=strike,
                option_right=option_right,
                stop_loss=stop_loss,
            )
            db.session.add(position)

    def get_positions(self, strategy: str = None) -> List[Dict]:
        """Get all open paper positions."""
        query = PaperPosition.query
        if strategy:
            query = query.filter_by(strategy=strategy)
        return [p.to_dict() for p in query.all()]

    def get_trades(self, limit: int = 50, offset: int = 0, strategy: str = None) -> Dict[str, Any]:
        """Get trade history with pagination."""
        query = PaperTrade.query
        if strategy:
            query = query.filter_by(strategy=strategy)
        total = query.count()
        trades = query.order_by(PaperTrade.timestamp.desc()).offset(offset).limit(limit).all()
        return {
            'trades': [t.to_dict() for t in trades],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    def get_cash_balance(self) -> float:
        """Calculate remaining cash = initial capital - cost of open positions + realized P&L."""
        positions = PaperPosition.query.all()
        # Cash used = sum of (avg_cost * quantity) for long positions
        # Cash received = sum of (avg_cost * |quantity|) for short positions (sold options)
        positions_cost = 0.0
        for p in positions:
            if p.security_type == 'OPTION':
                # Options: cost per contract = price * 100 shares
                positions_cost += p.avg_cost * p.quantity * 100
            else:
                positions_cost += p.avg_cost * p.quantity

        # Add realized P&L from closed trades
        realized = db.session.query(
            db.func.coalesce(db.func.sum(PaperTrade.pnl), 0)
        ).filter(PaperTrade.pnl.isnot(None)).scalar()

        return INITIAL_CAPITAL - positions_cost + float(realized)

    def get_portfolio_value(self) -> float:
        """Total portfolio value = cash + market value of positions."""
        cash = self.get_cash_balance()
        positions = PaperPosition.query.all()
        market_value = 0.0
        for p in positions:
            if p.current_price is not None:
                if p.security_type == 'OPTION':
                    market_value += p.current_price * p.quantity * 100
                else:
                    market_value += p.current_price * p.quantity
        return cash + market_value

    def update_prices(self):
        """Fetch current market prices for all open positions."""
        positions = PaperPosition.query.all()
        if not positions:
            return

        # Batch unique tickers
        tickers = set()
        for p in positions:
            if p.security_type == 'STOCK':
                tickers.add(p.ticker)

        # Fetch prices
        prices = {}
        for ticker in tickers:
            try:
                stock = DataProvider(ticker)
                info = stock.info
                price = (
                    info.get('currentPrice') or
                    info.get('regularMarketPrice') or
                    info.get('previousClose')
                )
                if price:
                    prices[ticker] = float(price)
            except Exception as e:
                logger.warning(f"Failed to get price for {ticker}: {e}")

        # Update positions
        for p in positions:
            if p.security_type == 'STOCK' and p.ticker in prices:
                p.current_price = prices[p.ticker]
                p.unrealized_pnl = (p.current_price - p.avg_cost) * p.quantity
            elif p.security_type == 'OPTION':
                # For options, estimate current value based on underlying price change
                # Simplified: use intrinsic value as approximation
                underlying_price = prices.get(p.ticker)
                if underlying_price and p.strike:
                    if p.option_right == 'CALL':
                        intrinsic = max(0, underlying_price - p.strike)
                    else:  # PUT
                        intrinsic = max(0, p.strike - underlying_price)
                    # Use max of intrinsic and a minimum time value estimate
                    p.current_price = max(intrinsic, p.avg_cost * 0.1)
                    p.unrealized_pnl = (p.current_price - p.avg_cost) * p.quantity * 100

        db.session.commit()
        logger.info(f"Updated prices for {len(prices)} tickers across {len(positions)} positions")

    def check_stop_losses(self):
        """Check and close positions that hit stop loss."""
        positions = PaperPosition.query.filter(PaperPosition.stop_loss.isnot(None)).all()
        closed = 0
        for p in positions:
            if p.current_price is None or p.security_type != 'STOCK':
                continue
            # Long position: close if price drops below stop loss
            if p.quantity > 0 and p.current_price <= p.stop_loss:
                logger.info(f"Stop loss triggered: {p.ticker} @ {p.current_price} (stop: {p.stop_loss})")
                self.execute_trade(
                    ticker=p.ticker, action='SELL', quantity=p.quantity,
                    price=p.current_price, strategy=p.strategy,
                    security_type='STOCK', notes=f'Stop loss triggered at {p.current_price}'
                )
                closed += 1
        if closed:
            logger.info(f"Closed {closed} positions via stop loss")

    def check_option_expiry(self):
        """Close options that are within 3 days of expiry."""
        positions = PaperPosition.query.filter_by(security_type='OPTION').all()
        today = date.today()
        closed = 0
        for p in positions:
            if not p.expiry:
                continue
            try:
                expiry_date = datetime.strptime(p.expiry, '%Y-%m-%d').date()
                days_to_expiry = (expiry_date - today).days
                if days_to_expiry <= 3:
                    close_price = p.current_price if p.current_price else 0.01
                    action = 'SELL' if p.quantity > 0 else 'BUY'
                    self.execute_trade(
                        ticker=p.ticker, action=action, quantity=abs(p.quantity),
                        price=close_price, strategy=p.strategy,
                        security_type='OPTION', expiry=p.expiry,
                        strike=p.strike, option_right=p.option_right,
                        notes=f'Auto-closed: {days_to_expiry} DTE'
                    )
                    closed += 1
            except (ValueError, TypeError):
                continue
        if closed:
            logger.info(f"Auto-closed {closed} expiring options")

    def calculate_daily_performance(self):
        """Create daily performance snapshot for all strategies."""
        today = date.today()

        # Check if already calculated
        existing = PaperPerformance.query.filter_by(date=today, strategy='combined').first()
        if existing:
            logger.info(f"Paper performance already calculated for {today}")
            return

        portfolio_value = self.get_portfolio_value()
        cash = self.get_cash_balance()
        positions = PaperPosition.query.all()

        # Get SPY benchmark
        spy_return = self._get_benchmark_return()

        # Get previous day's performance for daily return calculation
        prev = PaperPerformance.query.filter(
            PaperPerformance.date < today,
            PaperPerformance.strategy == 'combined'
        ).order_by(PaperPerformance.date.desc()).first()

        prev_nav = prev.nav if prev else 1.0
        current_nav = portfolio_value / INITIAL_CAPITAL
        daily_return = (current_nav / prev_nav - 1) * 100 if prev_nav else 0
        cumulative_return = (current_nav - 1) * 100

        # Calculate drawdown
        max_nav = db.session.query(
            db.func.max(PaperPerformance.nav)
        ).filter_by(strategy='combined').scalar() or 1.0
        max_nav = max(max_nav, current_nav)
        drawdown = (current_nav / max_nav - 1) * 100 if max_nav > 0 else 0

        prev_max_dd = prev.max_drawdown if prev else 0
        max_drawdown = min(drawdown, prev_max_dd) if prev_max_dd else drawdown

        # Save combined performance
        perf = PaperPerformance(
            date=today,
            strategy='combined',
            nav=round(current_nav, 6),
            daily_return=round(daily_return, 4),
            cumulative_return=round(cumulative_return, 4),
            drawdown=round(drawdown, 4),
            max_drawdown=round(max_drawdown, 4),
            benchmark_return=spy_return,
            position_count=len(positions),
            cash_balance=round(cash, 2),
        )
        db.session.add(perf)

        # Save per-strategy performance
        for strat in ['momentum', 'options_seller']:
            strat_positions = [p for p in positions if p.strategy == strat]
            strat_value = sum(
                (p.current_price or p.avg_cost) * abs(p.quantity) * (100 if p.security_type == 'OPTION' else 1)
                for p in strat_positions
            )
            # Simplified NAV for sub-strategy
            strat_perf = PaperPerformance(
                date=today,
                strategy=strat,
                nav=round(current_nav, 6),  # Use combined NAV as baseline
                daily_return=round(daily_return, 4),
                cumulative_return=round(cumulative_return, 4),
                drawdown=round(drawdown, 4),
                max_drawdown=round(max_drawdown, 4),
                benchmark_return=spy_return,
                position_count=len(strat_positions),
                cash_balance=round(cash, 2),
            )
            db.session.add(strat_perf)

        db.session.commit()
        logger.info(f"Paper performance saved: NAV={current_nav:.4f}, return={cumulative_return:.2f}%")

    def _get_benchmark_return(self) -> Optional[float]:
        """Get SPY cumulative return since paper trading started."""
        try:
            first_perf = PaperPerformance.query.filter_by(
                strategy='combined'
            ).order_by(PaperPerformance.date.asc()).first()

            stock = DataProvider('SPY')
            info = stock.info
            current_price = (
                info.get('currentPrice') or
                info.get('regularMarketPrice') or
                info.get('previousClose')
            )
            if not current_price:
                return None

            if first_perf and first_perf.benchmark_return is not None:
                # Use historical SPY price from first day
                # For simplicity, fetch via history
                hist = stock.history(period='6mo')
                if hist is not None and not hist.empty:
                    start_price = hist['Close'].iloc[0]
                    return round((float(current_price) / start_price - 1) * 100, 4)

            return 0.0
        except Exception as e:
            logger.warning(f"Failed to get SPY benchmark: {e}")
            return None

    def get_performance_summary(self) -> Dict[str, Any]:
        """Calculate summary KPI metrics."""
        performances = PaperPerformance.query.filter_by(
            strategy='combined'
        ).order_by(PaperPerformance.date.asc()).all()

        if not performances:
            return {
                'cumulative_return': 0,
                'annualized_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_rate': 0,
                'total_trades': 0,
                'running_days': 0,
                'account_value': INITIAL_CAPITAL,
            }

        latest = performances[-1]
        running_days = len(performances)
        cumulative_return = latest.cumulative_return or 0

        # Annualized return
        years = running_days / 252
        annualized = ((1 + cumulative_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Sharpe ratio (simplified: daily returns / daily std * sqrt(252))
        daily_returns = [p.daily_return for p in performances if p.daily_return is not None]
        if len(daily_returns) > 1:
            import statistics
            avg_ret = statistics.mean(daily_returns)
            std_ret = statistics.stdev(daily_returns)
            sharpe = (avg_ret / std_ret) * (252 ** 0.5) if std_ret > 0 else 0
        else:
            sharpe = 0

        # Win rate from trades
        trades = PaperTrade.query.filter(PaperTrade.pnl.isnot(None)).all()
        total_closed = len(trades)
        wins = len([t for t in trades if t.pnl and t.pnl > 0])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0

        total_trades = PaperTrade.query.count()

        return {
            'cumulative_return': round(cumulative_return, 2),
            'annualized_return': round(annualized, 2),
            'max_drawdown': round(latest.max_drawdown or 0, 2),
            'sharpe_ratio': round(sharpe, 2),
            'win_rate': round(win_rate, 1),
            'total_trades': total_trades,
            'running_days': running_days,
            'account_value': round(self.get_portfolio_value(), 2),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get paper trading engine status."""
        last_trade = PaperTrade.query.order_by(PaperTrade.timestamp.desc()).first()
        last_perf = PaperPerformance.query.filter_by(
            strategy='combined'
        ).order_by(PaperPerformance.date.desc()).first()

        return {
            'engine_running': True,
            'initial_capital': INITIAL_CAPITAL,
            'account_value': round(self.get_portfolio_value(), 2),
            'cash_balance': round(self.get_cash_balance(), 2),
            'open_positions': PaperPosition.query.count(),
            'total_trades': PaperTrade.query.count(),
            'last_trade_date': last_trade.timestamp.isoformat() if last_trade else None,
            'last_performance_date': last_perf.date.isoformat() if last_perf else None,
        }


# Singleton
paper_trading_service = PaperTradingService()
