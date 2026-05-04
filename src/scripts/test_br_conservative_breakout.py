# -*- coding: utf-8 -*-
from datetime import datetime, timezone, timedelta

from finam_core.strategy.br_conservative_breakout import BrConservativeBreakout


def main() -> int:
    s = BrConservativeBreakout(symbol="BRM6@RTSX")

    ts = datetime(2026, 5, 1, 7, 0, tzinfo=timezone.utc)

    # Русский комментарий: прогреваем M15 regime вверх.
    price = 80.0
    for i in range(40):
        price += 0.05
        s.on_regime_bar(
            ts=ts + timedelta(minutes=15 * i),
            open_=price - 0.03,
            high=price + 0.08,
            low=price - 0.08,
            close=price,
        )

    if not s.current_params.allow_trade:
        print(f"FAIL: online params block trading: {s.current_params}")
        return 1

    print("ONLINE_PARAMS", s.current_params)

    # Русский комментарий: прогреваем M5 диапазон.
    price = 82.0
    signal = None
    for i in range(35):
        close = price + i * 0.01
        signal = s.on_signal_bar(
            ts=ts + timedelta(minutes=5 * i),
            open_=close - 0.02,
            high=close + 0.05,
            low=close - 0.05,
            close=close,
        )

    # Русский комментарий: даём пробой вверх.
    signal = s.on_signal_bar(
        ts=ts + timedelta(minutes=5 * 36),
        open_=82.3,
        high=83.0,
        low=82.2,
        close=83.0,
    )

    if signal is None:
        print("FAIL: no signal")
        return 1

    if signal.side != "BUY":
        print(f"FAIL: unexpected side={signal.side}")
        return 1

    if "PRESET" not in signal.reason:
        print(f"FAIL: online preset was not used: {signal.reason}")
        return 1

    print("OK: BR conservative breakout signal generated")
    print(signal)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
