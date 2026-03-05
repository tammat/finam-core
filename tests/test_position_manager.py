from finam_core.accounting.position_manager import PositionManager

def main():
    pm = PositionManager()
    STARTING_CASH = float(os.getenv("STARTING_CASH", "100000"))

    pm = PositionManager()
    if hasattr(pm, "cash"):
        pm.cash = STARTING_CASH
    if hasattr(pm, "starting_cash"):
        pm.starting_cash = STARTING_CASH
    if hasattr(pm, "starting_capital"):
        pm.starting_capital = STARTING_CASH
    portfolio = PortfolioManager(starting_cash=100_000)
    # BUY 1 @100
    # жестко привязываем
    portfolio.position_manager = pm
    r1 = pm.apply_fill("TEST", "BUY", 1, 100)
    assert r1 == 0

    # SELL 1 @110
    r2 = pm.apply_fill("TEST", "SELL", 1, 110)
    assert r2 == 10

    print("ok: position manager works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())