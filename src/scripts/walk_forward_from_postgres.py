# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import itertools

from backtest_from_postgres import (
    parse_ts,
    load_bars,
    run_breakout_backtest,
)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe", default="M5")
    p.add_argument("--train-from", required=True)
    p.add_argument("--train-to", required=True)
    p.add_argument("--test-from", required=True)
    p.add_argument("--test-to", required=True)
    p.add_argument("--atr-period", type=int, default=14)
    p.add_argument("--fee-pct", type=float, default=0.0002)
    p.add_argument("--min-bars", type=int, default=300)
    args = p.parse_args()

    windows = [10, 15, 20, 30]
    stops = [1.5, 2.0, 2.5]
    takes = [1.5, 2.0, 2.5, 3.0]

    train_bars = load_bars(
        args.symbol,
        args.timeframe,
        parse_ts(args.train_from),
        parse_ts(args.train_to),
    )
    test_bars = load_bars(
        args.symbol,
        args.timeframe,
        parse_ts(args.test_from),
        parse_ts(args.test_to),
    )

    print("WALK_FORWARD_FROM_POSTGRES")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"train_bars={len(train_bars)}")
    print(f"test_bars={len(test_bars)}")

    if len(train_bars) < args.min_bars:
        print("STATUS=FAIL reason=NOT_ENOUGH_TRAIN_BARS")
        return 1
    if len(test_bars) < 50:
        print("STATUS=FAIL reason=NOT_ENOUGH_TEST_BARS")
        return 1

    results = []

    for w, s, t in itertools.product(windows, stops, takes):
        train = run_breakout_backtest(
            bars=train_bars,
            window=w,
            atr_period=args.atr_period,
            stop_atr=s,
            take_atr=t,
            fee_pct=args.fee_pct,
        )

        results.append({
            "window": w,
            "stop": s,
            "take": t,
            "train": train,
        })

    results.sort(
        key=lambda x: (
            x["train"]["pnl"],
            -abs(x["train"]["max_drawdown"]),
            x["train"]["winrate"],
        ),
        reverse=True,
    )

    best = results[0]

    test = run_breakout_backtest(
        bars=test_bars,
        window=best["window"],
        atr_period=args.atr_period,
        stop_atr=best["stop"],
        take_atr=best["take"],
        fee_pct=args.fee_pct,
    )

    print("BEST_TRAIN")
    print(f"window={best['window']}")
    print(f"stop_atr={best['stop']}")
    print(f"take_atr={best['take']}")
    print(f"train_trades={best['train']['trades']}")
    print(f"train_pnl={best['train']['pnl']}")
    print(f"train_winrate={best['train']['winrate']}%")
    print(f"train_max_drawdown={best['train']['max_drawdown']}")

    print("TEST_RESULT")
    print(f"test_trades={test['trades']}")
    print(f"test_pnl={test['pnl']}")
    print(f"test_winrate={test['winrate']}%")
    print(f"test_max_drawdown={test['max_drawdown']}")

    if test["pnl"] <= 0:
        print("STATUS=FAIL reason=OUT_OF_SAMPLE_NEGATIVE")
        return 1

    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
