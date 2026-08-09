#!/usr/bin/env python3
"""
UNIVERSE_TREND_PULLBACK_CANONICAL_FORENSIC_V1

Forensic canonical TREND_PULLBACK_V1 baseline.

Контракт:
- те же canonical parameters, что в baseline screen;
- тот же canonical trend_pullback_signal;
- только gross_pnl;
- 3 chronological OOS folds;
- boundary-crossing trades исключаются из fold;
- Bonferroni correction за все 5 baseline trials;
- никаких новых параметров;
- никаких execution costs;
- PostgreSQL read-only.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import statistics
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
    "universe_trend_pullback_canonical_adapter_screen_v1.json"
)

FOLD_COUNT = 3
MIN_FOLDS_PASSED = 2
MIN_FOLD_TRADES = 20
MAX_ADJUSTED_P = 0.05


def load_screen_module():
    """
    Загружает canonical screen как обычный Python module.

    Регистрация в sys.modules обязательна до exec_module:
    dataclasses в Python 3.13 используют cls.__module__
    для разрешения namespace класса.
    """
    import sys

    module_name = (
        "trend_pullback_canonical_screen_v1"
    )

    spec = importlib.util.spec_from_file_location(
        module_name,
        SCREEN_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "ERROR=CANONICAL_SCREEN_MODULE_LOAD_FAILED"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(
            module_name,
            None,
        )
        raise

    return module


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def gross_pnl_values(trades) -> list[float]:
    return [
        float(trade.gross_pnl)
        for trade in trades
    ]


def raw_p_value(trades) -> float:
    """
    Two-sided normal approximation for mean gross trade PnL.
    Multiple-testing correction применяется отдельно.
    """
    values = gross_pnl_values(trades)

    if len(values) < 2:
        return 1.0

    mean = statistics.fmean(values)
    stdev = statistics.stdev(values)

    if stdev <= 0:
        return 1.0

    z = abs(
        mean
        / (stdev / math.sqrt(len(values)))
    )

    return math.erfc(
        z / math.sqrt(2.0)
    )


def main() -> int:
    screen = load_screen_module()
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    symbols = list(cfg["symbols"])
    timeframe = cfg["timeframe"]

    canonical_parameters = dict(
        cfg["canonical_parameters"]
    )

    hold_bars = int(
        cfg["screen_exit_horizon"]["hold_bars"]
    )

    trade_parameters = dict(
        canonical_parameters
    )
    trade_parameters["hold_bars"] = hold_bars

    print(
        "=== UNIVERSE TREND PULLBACK "
        "CANONICAL FORENSIC V1 ==="
    )
    print("mode=canonical_true_gross_forensic")
    print("strategy_code=TREND_PULLBACK_V1")
    print("canonical_adapter_used=1")
    print("generic_execution_runner_used=0")
    print("signal_metric_source=GROSS_PNL")
    print("parameter_search_performed=0")
    print("execution_costs_used=0")
    print(f"multiple_testing_trials={len(symbols)}")
    print()

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        trial_rows = []

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
                        open=Decimal(
                            str(row["open"])
                        ),
                        high=Decimal(
                            str(row["high"])
                        ),
                        low=Decimal(
                            str(row["low"])
                        ),
                        close=Decimal(
                            str(row["close"])
                        ),
                        volume=Decimal(
                            str(row["volume"] or 0)
                        ),
                    )
                    for row in cur.fetchall()
                ]

                development_end = int(
                    len(bars)
                    * float(
                        cfg[
                            "development_fraction"
                        ]
                    )
                )

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

                total_trades = int(
                    metric["trades"]
                )
                pf = dec(
                    metric["profit_factor"]
                )
                expectancy = dec(
                    metric["expectancy"]
                )

                preliminary = (
                    total_trades
                    >= int(
                        cfg[
                            "minimum_oos_trades"
                        ]
                    )
                    and pf
                    >= dec(
                        cfg[
                            "minimum_oos_profit_factor"
                        ]
                    )
                    and expectancy
                    > dec(
                        cfg[
                            "minimum_oos_expectancy"
                        ]
                    )
                )

                # Fold boundaries задаём по OOS bar-time,
                # а не по числу сделок.
                oos_bar_count = (
                    len(bars)
                    - development_end
                )

                fold_size = math.ceil(
                    oos_bar_count / FOLD_COUNT
                )

                folds = []
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

                    # Только сделки, полностью лежащие
                    # внутри fold.
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

                    fold_count = int(
                        fold_metric["trades"]
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

                    fold_pass = (
                        fold_count
                        >= MIN_FOLD_TRADES
                        and fold_pf
                        >= Decimal("1.0")
                        and fold_expectancy
                        > Decimal("0")
                    )

                    if fold_pass:
                        folds_passed += 1

                    folds.append({
                        "fold": fold_no + 1,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "trades": fold_count,
                        "pf": fold_pf,
                        "expectancy":
                            fold_expectancy,
                        "pass": fold_pass,
                    })

                raw_p = raw_p_value(
                    trades
                )

                adjusted_p = min(
                    1.0,
                    raw_p * len(symbols),
                )

                forensic_pass = (
                    preliminary
                    and folds_passed
                    >= MIN_FOLDS_PASSED
                    and adjusted_p
                    <= MAX_ADJUSTED_P
                )

                trial_rows.append({
                    "symbol": symbol,
                    "preliminary": preliminary,
                    "forensic_pass":
                        forensic_pass,
                })

                if preliminary:
                    print(
                        "FORENSIC_ROW "
                        f"symbol={symbol} "
                        "strategy=TREND_PULLBACK_V1 "
                        f"oos_trades={total_trades} "
                        "gross_oos_profit_factor="
                        f"{pf} "
                        "gross_oos_expectancy="
                        f"{expectancy} "
                        f"folds_passed="
                        f"{folds_passed}/"
                        f"{FOLD_COUNT} "
                        f"raw_p={raw_p:.6f} "
                        f"adjusted_p="
                        f"{adjusted_p:.6f} "
                        f"forensic_pass="
                        f"{int(forensic_pass)}"
                    )

                    for fold in folds:
                        print(
                            "FOLD_ROW "
                            f"symbol={symbol} "
                            f"fold={fold['fold']} "
                            f"start_ts="
                            f"{fold['start_ts']} "
                            f"end_ts="
                            f"{fold['end_ts']} "
                            f"trades="
                            f"{fold['trades']} "
                            f"profit_factor="
                            f"{fold['pf']} "
                            f"expectancy="
                            f"{fold['expectancy']} "
                            f"pass="
                            f"{int(fold['pass'])}"
                        )

        preliminary_count = sum(
            1
            for row in trial_rows
            if row["preliminary"]
        )

        forensic_count = sum(
            1
            for row in trial_rows
            if row["forensic_pass"]
        )

        print()
        print(
            "SUMMARY_ROW "
            f"trials={len(trial_rows)} "
            f"preliminary_candidates="
            f"{preliminary_count} "
            f"forensic_candidates="
            f"{forensic_count}"
        )

        print("canonical_adapter_used=1")
        print("generic_execution_runner_used=0")
        print("signal_metric_source=GROSS_PNL")
        print("chronological_folds_used=1")
        print("fold_boundary_crossing_excluded=1")
        print("multiple_testing_adjusted=1")
        print("multiple_testing_trials=5")
        print("parameter_search_performed=0")
        print("economic_edge_claimed=0")
        print("execution_costs_used=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        verdict = (
            "UNIVERSE_TREND_PULLBACK_"
            "CANONICAL_FORENSIC_"
            + (
                "CANDIDATES_SURVIVE"
                if forensic_count
                else "NO_CANDIDATES_SURVIVE"
            )
        )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
