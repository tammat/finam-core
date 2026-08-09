#!/usr/bin/env python3
"""
UNIVERSE_READY_SIGNAL_CANDIDATE_FORENSIC_V1

Forensic gate для preliminary gross signal candidates.

Не ищет новые параметры.
Не использует execution costs.
Не пишет в PostgreSQL.

Дополнительные gates:
- исходный gross OOS candidate;
- 3 chronological folds;
- минимум 2 положительных folds;
- multiple-testing adjustment для всех 45 trials.
"""

from __future__ import annotations

import json
import math
import os
import statistics
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import (
    Bar,
    build_trades,
    metrics,
)
from finam_core.research.purged_split import (
    purged_bar_window,
    trades_in_purged_window,
)


CONFIG_PATH = Path(
    "config/research/universe_ready_signal_screen_v1.json"
)

STRATEGY_CODES = {
    "MOMENTUM": "MOMENTUM_CONTINUATION_V2",
    "MEAN_REVERSION": "MEAN_REVERSION_V2",
    "BREAKOUT": "VOLATILITY_BREAKOUT_V2",
}

FOLD_COUNT = 3
MIN_FOLDS_PASSED = 2
MAX_ADJUSTED_P = 0.05


def gross_metrics(trades) -> dict:
    """Signal-only metrics по Trade.gross_pnl."""
    values = [
        float(trade.gross_pnl)
        for trade in trades
    ]

    wins = [
        value
        for value in values
        if value > 0
    ]

    losses = [
        value
        for value in values
        if value <= 0
    ]

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    elif gross_win > 0:
        profit_factor = gross_win
    else:
        profit_factor = 0.0

    expectancy = (
        sum(values) / len(values)
        if values
        else 0.0
    )

    return {
        "trades": len(values),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "gross_pnl": sum(values),
    }


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def trade_pnl(trade) -> float:
    for field in ("gross_pnl", "net_pnl", "pnl"):
        value = getattr(trade, field, None)
        if value is not None:
            return float(value)
    return 0.0


def gross_trade_pnl(trade) -> float:
    """Статистический тест использует только gross signal PnL."""
    value = getattr(
        trade,
        "gross_pnl",
        None,
    )

    if value is None:
        return 0.0

    return float(value)


def raw_p_value(trades) -> float:
    values = [gross_trade_pnl(t) for t in trades]

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

    return math.erfc(z / math.sqrt(2.0))


def fold_result(trades) -> tuple[int, list[tuple]]:
    ordered = sorted(
        trades,
        key=lambda t: t.entry_ts,
    )

    if not ordered:
        return 0, []

    size = math.ceil(
        len(ordered) / FOLD_COUNT
    )

    passed = 0
    rows = []

    for fold_no in range(FOLD_COUNT):
        start = fold_no * size
        stop = min(
            (fold_no + 1) * size,
            len(ordered),
        )

        sample = ordered[start:stop]

        result = gross_metrics(sample)

        trades_count = int(
            result.get("trades") or 0
        )
        pf = dec(
            result.get("profit_factor")
        )
        expectancy = dec(
            result.get("expectancy")
        )

        fold_pass = (
            trades_count >= 10
            and pf >= Decimal("1.0")
            and expectancy > 0
        )

        if fold_pass:
            passed += 1

        rows.append(
            (
                fold_no + 1,
                trades_count,
                pf,
                expectancy,
                fold_pass,
            )
        )

    return passed, rows


def main() -> int:
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    print(
        "=== UNIVERSE READY SIGNAL "
        "CANDIDATE FORENSIC V1 ==="
    )
    print("mode=gross_candidate_forensic")
    print("parameter_search_performed=0")
    print("execution_costs_used=0")
    print("signal_metric_source=GROSS_PNL")
    print("economic_edge_claimed=0")
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

            for symbol in cfg["symbols"]:

                cur.execute(
                    """
                    SELECT ts,close
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND close IS NOT NULL
                    ORDER BY ts
                    """,
                    (
                        symbol,
                        cfg["timeframe"],
                    ),
                )

                bars = [
                    Bar(
                        row["ts"],
                        float(row["close"]),
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

                for family, variants in (
                    cfg["families"].items()
                ):
                    strategy_code = (
                        STRATEGY_CODES[family]
                    )

                    for variant_no, raw in enumerate(
                        variants,
                        start=1,
                    ):
                        params = dict(raw)
                        params["commission"] = 0.0
                        params["slippage"] = 0.0

                        oos_start, oos_stop, _ = (
                            purged_bar_window(
                                bars,
                                start=development_end,
                                end=len(bars),
                                parameters=params,
                            )
                        )

                        source_start = max(
                            0,
                            development_end
                            - int(
                                params["lookback"]
                            ),
                        )

                        generated = build_trades(
                            {
                                "strategy_code":
                                    strategy_code,
                                "parameter_json":
                                    params,
                            },
                            bars[source_start:],
                        )

                        oos = trades_in_purged_window(
                            generated,
                            start_ts=oos_start,
                            end_ts=oos_stop,
                        )

                        result = gross_metrics(oos)

                        count = int(
                            result.get("trades")
                            or 0
                        )
                        pf = dec(
                            result.get(
                                "profit_factor"
                            )
                        )
                        expectancy = dec(
                            result.get(
                                "expectancy"
                            )
                        )

                        preliminary = (
                            count
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

                        folds_passed, folds = (
                            fold_result(oos)
                        )

                        trial_rows.append({
                            "symbol": symbol,
                            "family": family,
                            "strategy":
                                strategy_code,
                            "variant":
                                variant_no,
                            "trades": count,
                            "pf": pf,
                            "expectancy":
                                expectancy,
                            "preliminary":
                                preliminary,
                            "raw_p":
                                raw_p_value(oos),
                            "folds_passed":
                                folds_passed,
                            "folds": folds,
                        })

        trials = len(trial_rows)
        promoted = []

        for row in trial_rows:
            adjusted_p = min(
                1.0,
                row["raw_p"] * trials,
            )

            forensic_pass = (
                row["preliminary"]
                and row["folds_passed"]
                >= MIN_FOLDS_PASSED
                and adjusted_p
                <= MAX_ADJUSTED_P
            )

            if row["preliminary"]:
                print(
                    "FORENSIC_ROW "
                    f"symbol={row['symbol']} "
                    f"family={row['family']} "
                    f"strategy={row['strategy']} "
                    f"variant={row['variant']} "
                    f"oos_trades={row['trades']} "
                    f"gross_oos_profit_factor="
                    f"{row['pf']} "
                    f"gross_oos_expectancy="
                    f"{row['expectancy']} "
                    f"folds_passed="
                    f"{row['folds_passed']}/"
                    f"{FOLD_COUNT} "
                    f"raw_p={row['raw_p']:.6f} "
                    f"adjusted_p={adjusted_p:.6f} "
                    f"forensic_pass="
                    f"{int(forensic_pass)}"
                )

                for (
                    fold_no,
                    count,
                    pf,
                    expectancy,
                    fold_pass,
                ) in row["folds"]:
                    print(
                        "FOLD_ROW "
                        f"symbol={row['symbol']} "
                        f"family={row['family']} "
                        f"variant={row['variant']} "
                        f"fold={fold_no} "
                        f"trades={count} "
                        f"profit_factor={pf} "
                        f"expectancy={expectancy} "
                        f"pass={int(fold_pass)}"
                    )

            if forensic_pass:
                promoted.append(row)

        preliminary_count = sum(
            1
            for row in trial_rows
            if row["preliminary"]
        )

        print()
        print(
            "SUMMARY_ROW "
            f"trials={trials} "
            f"preliminary_candidates="
            f"{preliminary_count} "
            f"forensic_candidates="
            f"{len(promoted)}"
        )

        print("multiple_testing_adjusted=1")
        print("chronological_folds_used=1")
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
            "UNIVERSE_READY_SIGNAL_FORENSIC_"
            + (
                "CANDIDATES_SURVIVE"
                if promoted
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
