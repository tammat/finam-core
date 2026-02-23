from accounting.portfolio_manager import PortfolioManager
from core.price_provider import InMemoryPriceProvider


class DummyFill:
    def __init__(self, fill_id, side, qty, price, commission=0.0):
        self.fill_id = fill_id
        self.side = side
        self.qty = qty
        self.price = price
        self.commission = commission
        self.symbol = "TEST"


def main():
    price_provider = InMemoryPriceProvider()
    pm = PortfolioManager(initial_cash=1000.0, price_provider=price_provider)

    # BUY 1 @100
    pm.on_fill(DummyFill("1", "BUY", 1.0, 100.0))

    state = pm.compute_state()
    assert state.equity == 1000.0  # no market price yet

    # inject market price
    price_provider.set_price("TEST", 110.0)

    state = pm.compute_state()

    assert state.unrealized_pnl == 10.0
    assert state.equity == 1010.0
    assert state.exposure == 110.0

    print("ok: mark-to-market works")


if __name__ == "__main__":
    raise SystemExit(main())