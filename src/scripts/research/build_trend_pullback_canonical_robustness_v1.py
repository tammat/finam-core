#!/usr/bin/env python3
"""
TREND_PULLBACK_CANONICAL_ROBUSTNESS_V1

Локальная robustness-проверка трех forensic survivors.

Не выполняет optimization.
Не выбирает лучший variant.
Не использует execution costs.
Signal metric: только gross_pnl.
Canonical implementation: trend_pullback_signal().
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras


ROOT = Path("/opt/finam-core")

SCREEN_PATH = ROOT / (
    "src/scripts/research/"
    "build_universe_trend_pullback_canonical_adapter_screen_v1.py"
)

CONFIG_PATH = ROOT / (
    "config/research/"
    "trend_pullback_canonical_robustness_v1.json"
)

FOLD_COUNT = 3


def load_screen():
    name = "trend_pullback_canonical_screen_for_robustness"

    spec = importlib.util.spec_from_file_location(
        name,
        SCREEN_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "ERROR=CANONICAL_SCREEN_IMPORT_SPEC_FAILED"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise

    return module


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def main() -> int:
    screen = load_screen()

    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    symbols = list(cfg["symbols"])
    variants = list(cfg["variants"])
    timeframe = cfg["timeframe"]

    hold_bars = int(
        cfg["screen_exit_horizon"]["hold_bars"]
    )

    print(
        "=== TREND PULLBACK CANONICAL "
        "ROBUSTNESS V1 ==="
    )
    print("mode=canonical_local_robustness")
    print("strategy_code=TREND_PULLBACK_V1")
    print(f"symbols={len(symbols)}")
    print(f"variants={len(variants)}")
    print("canonical_adapter_used=1")
    print("generic_execution_runner_used=0")
    print("signal_metric_source=GROSS_PNL")
    print("parameter_optimization_performed=0")
    print("execution_costs_used=0")
    print()

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        symbol_results = []

        with conn.cursor(
            cursor_factory=(
                psycopg2.extras.RealDictCursor
            )
        ) as cur:

            for symbol in symbols:
                cur.execute(
                    """
                    SELECT
                        ts,
                        open,
                        high,
                        low,
                        close,
                        COALESCE(volume,0) AS volume
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND open IS NOT NULL
                      AND high IS NOT NULL
                      AND low IS NOT NULL
                      AND close IS NOT NULL
                    ORDER BY ts
                    """,
                    (
                        symbol,
                        timeframe,
                    ),
                )

                bars = [
                    screen.MarketBar(
                        ts=row["ts"],
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        volume=Decimal(
                            str(row["volume"] or 0)
                        ),
                    )
                    for row in cur.fetchall()
                ]

                development_end = int(
                    len(bars)
                    * float(
                        cfg["development_fraction"]
                    )
                )

                positive_variants = 0
                stable_fold_variants = 0

                for variant in variants:
                    variant_code = variant["code"]

                    parameters = {
                        key: value
                        for key, value
                        in variant.items()
                        if key != "code"
                    }

                    trade_parameters = dict(
                        parameters
                    )

                    trade_parameters[
                        "hold_bars"
                    ] = hold_bars

                    trades = (
                        screen.build_canonical_trades(
                            bars,
                            trade_parameters,
                            development_end,
                            len(bars),
                        )
                    )

                    metric = screen.gross_metrics(
                        trades
                    )

                    trade_count = int(
                        metric["trades"]
                    )

                    pf = dec(
                        metric["profit_factor"]
                    )

                    expectancy = dec(
                        metric["expectancy"]
                    )

                    positive = (
                        trade_count
                        >= int(
                            cfg["minimum_oos_trades"]
                        )
                        and pf
                        > Decimal("1.0")
                        and expectancy
                        > Decimal("0")
                    )

                    if positive:
                        positive_variants += 1

                    # Temporal robustness для каждого
                    # соседнего parameter set.
                    oos_count = (
                        len(bars)
                        - development_end
                    )

                    fold_size = math.ceil(
                        oos_count / FOLD_COUNT
                    )

                    folds_passed = 0

                    for fold_no in range(
                        FOLD_COUNT
                    ):
                        start_index = (
                            development_end
                            + fold_no * fold_size
                        )

                        stop_index = min(
                            development_end
                            + (fold_no + 1)
                            * fold_size,
                            len(bars),
                        )

                        if start_index >= stop_index:
                            continue

                        start_ts = bars[
                            start_index
                        ].ts

                        end_ts = bars[
                            stop_index - 1
                        ].ts

                        fold_trades = [
                            trade
                            for trade in trades
                            if (
                                trade.entry_ts
                                >= start_ts
                                and trade.exit_ts
                                <= end_ts
                            )
                        ]

                        fold_metric = (
                            screen.gross_metrics(
                                fold_trades
                            )
                        )

                        fold_pf = dec(
                            fold_metric[
                                "profit_factor"
                            ]
                        )

                        fold_expectancy = dec(
                            fold_metric[
                                "expectancy"
                            ]
                        )

                        fold_trade_count = int(
                            fold_metric[
                                "trades"
                            ]
                        )

                        fold_pass = (
                            fold_trade_count >= 20
                            and fold_pf
                            > Decimal("1.0")
                            and fold_expectancy
                            > Decimal("0")
                        )

                        if fold_pass:
                            folds_passed += 1

                        print(
                            "ROBUSTNESS_FOLD_ROW "
                            f"symbol={symbol} "
                            f"variant={variant_code} "
                            f"fold={fold_no + 1} "
                            f"trades={fold_trade_count} "
                            f"profit_factor={fold_pf} "
                            f"expectancy="
                            f"{fold_expectancy} "
                            f"pass={int(fold_pass)}"
                        )

                    fold_stable = (
                        folds_passed >= 2
                    )

                    if fold_stable:
                        stable_fold_variants += 1

                    print(
                        "ROBUSTNESS_ROW "
                        f"symbol={symbol} "
                        f"variant={variant_code} "
                        f"fast_ma_period="
                        f"{parameters['fast_ma_period']} "
                        f"slow_ma_period="
                        f"{parameters['slow_ma_period']} "
                        f"atr_period="
                        f"{parameters['atr_period']} "
                        "pullback_atr_multiplier="
                        f"{parameters['pullback_atr_multiplier']} "
                        f"oos_trades={trade_count} "
                        f"gross_oos_profit_factor={pf} "
                        f"gross_oos_expectancy="
                        f"{expectancy} "
                        f"positive={int(positive)} "
                        f"folds_passed="
                        f"{folds_passed}/{FOLD_COUNT} "
                        f"fold_stable="
                        f"{int(fold_stable)}"
                    )

                positive_ratio = (
                    positive_variants
                    / len(variants)
                )

                stable_ratio = (
                    stable_fold_variants
                    / len(variants)
                )

                robust = (
                    positive_ratio
                    >= float(
                        cfg[
                            "minimum_positive_neighbor_ratio"
                        ]
                    )
                    and stable_ratio
                    >= float(
                        cfg[
                            "minimum_positive_neighbor_ratio"
                        ]
                    )
                )

                symbol_results.append(
                    (
                        symbol,
                        robust,
                    )
                )

                print(
                    "SYMBOL_ROBUSTNESS_ROW "
                    f"symbol={symbol} "
                    f"positive_variants="
                    f"{positive_variants}/"
                    f"{len(variants)} "
                    f"fold_stable_variants="
                    f"{stable_fold_variants}/"
                    f"{len(variants)} "
                    f"positive_ratio="
                    f"{positive_ratio:.4f} "
                    f"fold_stable_ratio="
                    f"{stable_ratio:.4f} "
                    f"robust={int(robust)}"
                )

        robust_symbols = [
            symbol
            for symbol, robust
            in symbol_results
            if robust
        ]

        print()
        print(
            "SUMMARY_ROW "
            f"symbols={len(symbols)} "
            f"variants_per_symbol="
            f"{len(variants)} "
            f"trials="
            f"{len(symbols) * len(variants)} "
            f"robust_symbols="
            f"{len(robust_symbols)}"
        )

        print(
            "robust_symbol_names="
            + (
                ",".join(robust_symbols)
                if robust_symbols
                else "NONE"
            )
        )

        print("canonical_adapter_used=1")
        print("generic_execution_runner_used=0")
        print("signal_metric_source=GROSS_PNL")
        print("local_parameter_neighborhood_used=1")
        print("one_parameter_at_a_time=1")
        print("parameter_optimization_performed=0")
        print("chronological_folds_used=1")
        print("execution_costs_used=0")
        print("economic_edge_claimed=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        verdict = (
            "TREND_PULLBACK_CANONICAL_"
            "ROBUSTNESS_"
            + (
                "SURVIVORS_CONFIRMED"
                if robust_symbols
                else "NO_SURVIVORS"
            )
        )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
