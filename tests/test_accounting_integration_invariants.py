import pytest

from finam_core.accounting.portfolio_manager import PortfolioManager


class DummyFill:
    def __init__(self, symbol, qty, price):
        self.symbol = symbol
        self.qty = qty
        self.price = price


def test_accounting_equity_invariants():

    pm = PortfolioManager(starting_cash=100_000)

    # 1️⃣ BUY 1 @ 10_000
    pm.apply(DummyFill("NG", 1, 10_000))

    # 2️⃣ Mark to market @ 11_000
    pm.mark_price("NG", 11_000)

    # 3️⃣ SELL 1 @ 12_000
    pm.apply(DummyFill("NG", -1, 12_000))

    context = pm.get_context()

    # ---- invariant 1: no open positions ----
    assert context.positions.get("NG").qty == 0

    # ---- invariant 2: unrealized pnl == 0 ----
    assert context.unrealized_pnl == 0

    # ---- invariant 3: realized pnl correct ----
    assert context.realized_pnl == 2_000

    # ---- invariant 4: equity matches ----
    expected_equity = 100_000 + 2_000
    assert context.equity == expected_equity