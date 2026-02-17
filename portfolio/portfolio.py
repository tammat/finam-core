from dataclasses import dataclass
from data.asset_metadata import get_asset_metadata

@dataclass
class Position:
    symbol: str
    asset_class: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0


class Portfolio:
    """
    Institutional-ready portfolio model.
    Tracks:
    - cash
    - positions
    - basic exposure
    """

    def __init__(self, starting_cash=100_000.0):
        self.cash = float(starting_cash)
        self.positions = {}

    def on_fill(self, fill):
        metadata = get_asset_metadata(fill.symbol)
        asset_class = metadata["asset_class"]
        pos = self.positions.get(fill.symbol)

        signed_qty = fill.quantity if fill.side == "BUY" else -fill.quantity

        if not pos:
            pos = Position(
                symbol=fill.symbol,
                asset_class=asset_class,
                qty=0.0,
                avg_price=0.0,
            )

        new_qty = pos.qty + signed_qty

        # average price update (simple version)
        if new_qty != 0:
            total_cost = pos.avg_price * abs(pos.qty) + fill.price * abs(signed_qty)
            pos.avg_price = total_cost / (abs(pos.qty) + abs(signed_qty))

        pos.qty = new_qty

        self.positions[fill.symbol] = pos

        # update cash
        self.cash -= signed_qty * fill.price

    def total_exposure_fraction(self):
        exposure = sum(abs(p.qty) for p in self.positions.values())
        return exposure / 1000.0

    def calculate_position_size(self, signal):
        return 1.0

    def current_equity(self, price_resolver=None):
        """
        Equity = cash + unrealized PnL
        price_resolver: функция получения последней цены
        """
        unrealized = 0.0

        if price_resolver:
            for symbol, pos in self.positions.items():
                if pos.qty == 0:
                    continue

                current_price = price_resolver(symbol)
                unrealized += (current_price - pos.avg_price) * pos.qty

                pos.unrealized_pnl = (current_price - pos.avg_price) * pos.qty

        return self.cash + unrealized