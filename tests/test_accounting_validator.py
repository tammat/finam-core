from accounting.portfolio_manager import PortfolioManager

class DummyFill:
    def __init__(self, fill_id, side, qty, price, commission=0.0, realized_pnl=0.0):
        self.fill_id = fill_id
        self.side = side
        self.qty = qty
        self.price = price
        self.commission = commission
        self.realized_pnl = realized_pnl

def _must_fail(fn, contains: str) -> None:
    try:
        fn()
    except RuntimeError as e:
        s = str(e)
        if contains not in s:
            raise SystemExit(f"expected error containing {contains!r}, got: {s}")
        return
    raise SystemExit("expected failure, but it passed")


def main() -> int:
    # --- OK path ---
    pm = PortfolioManager(initial_cash=1000.0)

    pm.on_fill(DummyFill("1", "BUY", 1.0, 100.0, commission=1.0, realized_pnl=0.0))
    pm.on_fill(DummyFill("2", "SELL", 1.0, 110.0, commission=1.0, realized_pnl=10.0))
    # --- BAD path: positive fees should fail (FEES_SIGN) ---
    def case_positive_fee():
        pm2 = PortfolioManager(initial_cash=1000.0)
        pm2.on_fill(DummyFill("bad", "BUY", 1.0, 100.0, commission=-1.0, realized_pnl=0.0))
            # при этом realized_pnl -= commission => realized_pnl +=1 (и fees>0 в snapshot)
        # валидатор должен упасть

    _must_fail(case_positive_fee, "INVALID_COMMISSION_SIGN")
    print("ok: accounting validator integration passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())