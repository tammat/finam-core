# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import itertools



def score_result(result: dict, overtrade_limit: int = 80) -> float:
    """Русский комментарий: устойчивый score вместо выбора только по train PnL."""
    pnl = float(result.get("pnl", 0.0) or 0.0)
    max_dd = abs(float(result.get("max_drawdown", 0.0) or 0.0))
    winrate = float(result.get("winrate", 0.0) or 0.0)
    trades = int(result.get("trades", 0) or 0)

    drawdown_penalty = max_dd * 1.5
    overtrade_penalty = max(0, trades - overtrade_limit) * 0.05
    winrate_bonus = max(0.0, winrate - 50.0) * 0.03

    return round(pnl - drawdown_penalty - overtrade_penalty + winrate_bonus, 6)

from backtest_from_postgres import (
    parse_ts,
    load_bars,
    run_breakout_backtest,
    build_regime_map,
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
    p.add_argument("--top-n", type=int, default=5)
    p.add_argument("--regime-timeframe", default=None)
    p.add_argument("--regime-fast", type=int, default=5)
    p.add_argument("--regime-slow", type=int, default=20)
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

    train_regime_map = []
    test_regime_map = []
    if args.regime_timeframe:
        train_regime_bars = load_bars(
            args.symbol,
            args.regime_timeframe,
            parse_ts(args.train_from),
            parse_ts(args.train_to),
        )
        test_regime_bars = load_bars(
            args.symbol,
            args.regime_timeframe,
            parse_ts(args.test_from),
            parse_ts(args.test_to),
        )
        train_regime_map = build_regime_map(
            regime_bars=train_regime_bars,
            fast_period=args.regime_fast,
            slow_period=args.regime_slow,
        )
        test_regime_map = build_regime_map(
            regime_bars=test_regime_bars,
            fast_period=args.regime_fast,
            slow_period=args.regime_slow,
        )

    print("WALK_FORWARD_FROM_POSTGRES")
    print(f"symbol={args.symbol}")
    print(f"timeframe={args.timeframe}")
    print(f"train_bars={len(train_bars)}")
    print(f"test_bars={len(test_bars)}")
    if args.regime_timeframe:
        print(f"regime_timeframe={args.regime_timeframe}")
        print(f"regime_fast={args.regime_fast}")
        print(f"regime_slow={args.regime_slow}")
        print(f"train_regime_points={len(train_regime_map)}")
        print(f"test_regime_points={len(test_regime_map)}")

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
            regime_map=train_regime_map,
        )

        results.append({
            "window": w,
            "stop": s,
            "take": t,
            "train": train,
            "train_score": score_result(train),
        })

    results.sort(
        key=lambda x: (
            x["train_score"],
            x["train"]["pnl"],
            -abs(x["train"]["max_drawdown"]),
            x["train"]["winrate"],
        ),
        reverse=True,
    )

    top = results[: max(1, args.top_n)]

    print("TOP_TRAIN")
    for i, item in enumerate(top, start=1):
        tr = item["train"]
        print(
            f"rank={i} window={item['window']} stop_atr={item['stop']} take_atr={item['take']} "
            f"train_score={item['train_score']} train_pnl={tr['pnl']} "
            f"train_trades={tr['trades']} train_winrate={tr['winrate']}% "
            f"train_max_drawdown={tr['max_drawdown']}"
        )

    tested = []
    for item in top:
        test = run_breakout_backtest(
            bars=test_bars,
            window=item["window"],
            atr_period=args.atr_period,
            stop_atr=item["stop"],
            take_atr=item["take"],
            fee_pct=args.fee_pct,
            regime_map=test_regime_map,
        )
        tested.append({
            **item,
            "test": test,
            "test_score": score_result(test, overtrade_limit=40),
        })

    tested.sort(
        key=lambda x: (
            x["test_score"],
            x["test"]["pnl"],
            -abs(x["test"]["max_drawdown"]),
            x["test"]["winrate"],
        ),
        reverse=True,
    )

    best = tested[0]
    test = best["test"]

    print("BEST_WALK_FORWARD")
    print(f"window={best['window']}")
    print(f"stop_atr={best['stop']}")
    print(f"take_atr={best['take']}")
    print(f"train_score={best['train_score']}")
    print(f"train_trades={best['train']['trades']}")
    print(f"train_pnl={best['train']['pnl']}")
    print(f"train_winrate={best['train']['winrate']}%")
    print(f"train_max_drawdown={best['train']['max_drawdown']}")

    print("TEST_RESULT")
    print(f"test_trades={test['trades']}")
    print(f"test_pnl={test['pnl']}")
    print(f"test_winrate={test['winrate']}%")
    print(f"test_max_drawdown={test['max_drawdown']}")
    print(f"test_score={best['test_score']}")

    if test["pnl"] <= 0:
        print("STATUS=FAIL reason=OUT_OF_SAMPLE_NEGATIVE")
        return 1

    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
