from dataclasses import dataclass
from typing import Dict
from collections import defaultdict


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    market_price: float = 0.0


class PositionManager:

    def __init__(self, starting_cash: float = 0.0):
        self.cash = float(starting_cash)

        self.positions: Dict[str, Position] = defaultdict(
            lambda: Position(symbol="")
        )
        self.starting_cash = starting_cash
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.processed_fills = set()
        self._peak_equity = float(starting_cash)
        self.daily_realized_pnl = 0.0

    # --------------------------------------------------

    def apply_fill(self, fill):

        if fill.fill_id in self.processed_fills:
            return

        self.processed_fills.add(fill.fill_id)

        pos = self.positions[fill.symbol]

        signed_qty = fill.qty if fill.side == "BUY" else -fill.qty

        # Increase / open
        if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
            new_qty = pos.qty + signed_qty

            if new_qty != 0:
                pos.avg_price = (
                    pos.qty * pos.avg_price + signed_qty * fill.price
                ) / new_qty

            pos.qty = new_qty

        # Reduce / close
        else:
            closing = min(abs(pos.qty), abs(signed_qty))
            pnl = closing * (fill.price - pos.avg_price)

            if pos.qty < 0:
                pnl = -pnl

            pos.realized_pnl += pnl
            pos.qty += signed_qty

            if pos.qty == 0:
                pos.avg_price = 0.0

        # Cash update
        self.cash -= signed_qty * fill.price
        self.cash -= fill.commission

    # --------------------------------------------------

    def update_market_price(self, symbol: str, price: float):
        pos = self.positions[symbol]
        pos.market_price = price
        if symbol in self.positions:
            self.positions[symbol].market_price = price

        self._recalculate_unrealized()

    # --------------------------------------------------

    def total_equity(self):

        market_value = sum(
            p.qty * (p.market_price if p.market_price else p.avg_price)
            for p in self.positions.values()
        )

        equity = self.cash + market_value

        if equity > self._peak_equity:
            self._peak_equity = equity

        return equity

    # --------------------------------------------------

    def current_drawdown(self):

        equity = self.total_equity()

        if self._peak_equity == 0:
            return 0.0

        return (equity - self._peak_equity) / self._peak_equity

    # --------------------------------------------------

    def get_context(self):

        class Context:
            pass

        context = Context()

        # -------------------------------
        # Equity
        # -------------------------------
        context.equity = (
                self.starting_cash
                + self.realized_pnl
                + self.unrealized_pnl
        )
        context.realized_pnl = self.realized_pnl
        context.unrealized_pnl = self.unrealized_pnl
        # -------------------------------
        # Peak equity (capital protection)
        # -------------------------------
        if not hasattr(self, "peak_equity"):
            self.peak_equity = float(self.starting_cash)

        if context.equity > self.peak_equity:
            self.peak_equity = context.equity

        context.peak_equity = self.peak_equity

        # drawdown (negative value)
        if self.peak_equity != 0:
            context.drawdown = (
                    (context.equity - self.peak_equity)
                    / self.peak_equity
            )
        else:
            context.drawdown = 0.0
        # -------------------------------
        # Daily loss
        # -------------------------------
        daily_pnl = getattr(self, "daily_realized_pnl", 0.0)

        context.daily_realized_pnl = daily_pnl

        if self.starting_cash != 0:
            context.daily_drawdown = daily_pnl / self.starting_cash
        else:
            context.daily_drawdown = 0.0
        # -------------------------------
        # Gross exposure
        # -------------------------------
        context.gross_exposure = sum(
            abs(pos.qty) * pos.avg_price
            for pos in self.positions.values()
        )

        context.positions = self.positions

        # -------------------------------
        # Portfolio Heat
        # -------------------------------
        portfolio_heat = 0.0

        for symbol, pos in self.positions.items():
            if pos.qty == 0:
                continue

            atr = getattr(pos, "atr", None)

            if atr:
                portfolio_heat += abs(pos.qty) * atr
            else:
                portfolio_heat += abs(pos.qty) * pos.avg_price

        context.portfolio_heat = portfolio_heat

        return context
    # --------------------------------------------------

    def on_fill(self, fill):
        self.apply_fill(fill)

    def on_market_data(self, market_data):
        symbol = market_data.symbol
        price = market_data.price
        self.update_market_price(symbol, price)

    def _recalculate_unrealized(self):

        total = 0.0

        for symbol, pos in self.positions.items():
            if pos.qty == 0:
                continue

            market_price = getattr(pos, "market_price", None)
            if market_price is None:
                continue

            total += (market_price - pos.avg_price) * pos.qty

        self.unrealized_pnl = total