from domain.position_manager import PositionManager


def main():
    pm = PositionManager()

    # BUY 1 @100
    r1 = pm.apply_fill("TEST", "BUY", 1, 100)
    assert r1 == 0

    # SELL 1 @110
    r2 = pm.apply_fill("TEST", "SELL", 1, 110)
    assert r2 == 10

    print("ok: position manager works")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())