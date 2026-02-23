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
    provider = InMemoryPriceProvider()
    pm = PortfolioManager(initial_cash=100000.0, price_provider=provider)

    # BUY 10 @100
    pm.on_fill(DummyFill("1", "BUY", 10.0, 100.0))

    # 10 000 price updates
    price = 100.0
    for i in range(10000):
        price += 0.0001
        provider.set_price("TEST", price)
        state = pm.compute_state()

    # Теоретический результат
    expected_unrealized = (price - 100.0) * 10.0
    expected_equity = 100000.0 - 1000.0 + (10.0 * price)

    assert abs(state.unrealized_pnl - expected_unrealized) < 1e-9
    assert abs(state.equity - expected_equity) < 1e-9

    print("ok: mtm stress stable")


if __name__ == "__main__":
    raise SystemExit(main())