from collections import defaultdict
from dataclasses import dataclass
from risk.context import RiskContext

@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0

class PositionManager:

    def __init__(self, starting_cash: float = 100_000):
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.positions = defaultdict(Position)
        self.processed_fills = set()  # idempotency
        self.last_prices = {}  # mark-to-market

    # ---------- CONTEXT ----------
    def get_context(self) -> RiskContext:

        gross = 0.0
        net = 0.0
        unrealized = 0.0

        for symbol, pos in self.positions.items():
            price = self.last_prices.get(symbol, pos.avg_price)
            notional = pos.qty * price
            gross += abs(notional)
            net += notional
            unrealized += (price - pos.avg_price) * pos.qty

        equity = self.cash + unrealized

        return RiskContext(
            equity=equity,
            cash=self.cash,
            gross_exposure=gross,
            net_exposure=net,
        )

    # ---------- APPLY FILL ----------
    def apply_fill(self, fill):

        if fill.fill_id in self.processed_fills:
            return  # idempotency

        pos = self.positions[fill.symbol]

        if fill.side == "BUY":

            if pos.qty >= 0:
                total_cost = pos.qty * pos.avg_price + fill.qty * fill.price
                pos.qty += fill.qty
                pos.avg_price = total_cost / pos.qty
            else:
                # short closing
                closing_qty = min(abs(pos.qty), fill.qty)
                pnl = (pos.avg_price - fill.price) * closing_qty
                pos.realized_pnl += pnl
                pos.qty += fill.qty
                if pos.qty > 0:
                    pos.avg_price = fill.price

            self.cash -= fill.qty * fill.price + fill.commission

        elif fill.side == "SELL":

            if pos.qty <= 0:
                total_cost = abs(pos.qty) * pos.avg_price + fill.qty * fill.price
                pos.qty -= fill.qty
                pos.avg_price = total_cost / abs(pos.qty)
            else:
                closing_qty = min(pos.qty, fill.qty)
                pnl = (fill.price - pos.avg_price) * closing_qty
                pos.realized_pnl += pnl
                pos.qty -= fill.qty
                if pos.qty < 0:
                    pos.avg_price = fill.price

            self.cash += fill.qty * fill.price - fill.commission

        self.processed_fills.add(fill.fill_id)

    # ---------- MARKET UPDATE ----------
    def update_market_price(self, symbol, price):
        self.last_prices[symbol] = price


