from dataclasses import dataclass
from finam_core.backtest.vol_sizer import VolatilitySizer


@dataclass
class SimpleSignal:
    side: str
    qty: float

    def to_fill(self, price: float):
        from finam_core.accounting.fill import Fill
        return Fill(
            fill_id="bt",
            side=self.side,
            qty=self.qty,
            price=price,
            commission=0.0,
            realized_pnl=0.0
        )


class SimpleTrendStrategy:

    def __init__(self):
        self.prev_close = None
        self.sizer = VolatilitySizer()

    def on_bar(self, bar, equity):

        vol = self.sizer.update(bar.close, self.prev_close)

        signal = None

        if self.prev_close and bar.close > self.prev_close:
            qty = self.sizer.size(equity, bar.close, vol)
            if qty > 0:
                signal = SimpleSignal("BUY", qty)

        self.prev_close = bar.close
        return signal