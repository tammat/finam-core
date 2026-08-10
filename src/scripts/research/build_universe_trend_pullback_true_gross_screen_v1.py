#!/usr/bin/env python3
"""
UNIVERSE_TREND_PULLBACK_TRUE_GROSS_SCREEN_V1

Frozen single-asset true-gross OOS screen для TREND_PULLBACK_V1.

Контракт:
- только READY symbols;
- predefined variants;
- chronological + purged OOS;
- signal metrics только по gross_pnl;
- execution costs не участвуют;
- PostgreSQL read-only;
- никаких runtime/execution changes.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import (
    Bar,
    build_trades,
)
from finam_core.research.purged_split import (
    purged_bar_window,
    trades_in_purged_window,
)


CONFIG_PATH = Path(
    "config/research/"
    "universe_trend_pullback_true_gross_screen_v1.json"
)


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def gross_metrics(trades) -> dict:
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


def main() -> int:
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    symbols = list(cfg["symbols"])
    timeframe = cfg["timeframe"]
    strategy_code = cfg["strategy_code"]

    print(
        "=== UNIVERSE TREND PULLBACK "
        "TRUE GROSS SCREEN V1 ==="
    )
    print("mode=true_gross_signal_screen")
    print(f"strategy_code={strategy_code}")
    print(f"timeframe={timeframe}")
    print(f"symbols={len(symbols)}")
    print(
        f"variants={len(cfg['variants'])}"
    )
    print("parameter_search_performed=0")
    print("execution_costs_used=0")
    print("signal_metric_source=GROSS_PNL")
    print()

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        all_results = []
        candidates = []

        with conn.cursor(
            cursor_factory=(
                psycopg2.extras.RealDictCursor
            )
        ) as cur:

            for symbol in symbols:
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
                        timeframe,
                    ),
                )

                bars = [
                    Bar(
                        row["ts"],
                        float(row["close"]),
                    )
                    for row in cur.fetchall()
                ]

                print(
                    "SYMBOL_ROW "
                    f"symbol={symbol} "
                    f"bars={len(bars)}"
                )

                if len(bars) < int(
                    cfg["minimum_bars"]
                ):
                    print(
                        "SYMBOL_SKIP "
                        f"symbol={symbol} "
                        "reason=INSUFFICIENT_BARS"
                    )
                    continue

                development_end = int(
                    len(bars)
                    * float(
                        cfg[
                            "development_fraction"
                        ]
                    )
                )

                for variant_no, raw_params in enumerate(
                    cfg["variants"],
                    start=1,
                ):
                    params = dict(
                        raw_params
                    )

                    # Не позволяем execution economics
                    # попасть в signal screen.
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

                    warmup = max(
                        int(params["fast_ma"]),
                        int(params["slow_ma"]),
                    )

                    source_start = max(
                        0,
                        development_end - warmup,
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

                    oos_trades = (
                        trades_in_purged_window(
                            generated,
                            start_ts=oos_start,
                            end_ts=oos_stop,
                        )
                    )

                    metric = gross_metrics(
                        oos_trades
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

                    candidate = (
                        trade_count
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

                    row = {
                        "symbol": symbol,
                        "variant": variant_no,
                        "trades": trade_count,
                        "pf": pf,
                        "expectancy": expectancy,
                        "gross_pnl": dec(
                            metric["gross_pnl"]
                        ),
                        "candidate": candidate,
                    }

                    all_results.append(
                        row
                    )

                    if candidate:
                        candidates.append(
                            row
                        )

                    print(
                        "SCREEN_ROW "
                        f"symbol={symbol} "
                        f"strategy="
                        f"{strategy_code} "
                        f"variant={variant_no} "
                        f"oos_trades="
                        f"{trade_count} "
                        "gross_oos_profit_factor="
                        f"{pf} "
                        "gross_oos_expectancy="
                        f"{expectancy} "
                        "gross_oos_pnl="
                        f"{row['gross_pnl']} "
                        "signal_candidate="
                        f"{int(candidate)}"
                    )

        print()
        print("CANDIDATE_ROWS")

        ranked = sorted(
            candidates,
            key=lambda row: (
                row["expectancy"],
                row["pf"],
                row["trades"],
            ),
            reverse=True,
        )

        for rank, row in enumerate(
            ranked,
            start=1,
        ):
            print(
                "CANDIDATE_ROW "
                f"rank={rank} "
                f"symbol={row['symbol']} "
                f"strategy={strategy_code} "
                f"variant={row['variant']} "
                f"oos_trades={row['trades']} "
                "gross_oos_profit_factor="
                f"{row['pf']} "
                "gross_oos_expectancy="
                f"{row['expectancy']} "
                "gross_oos_pnl="
                f"{row['gross_pnl']}"
            )

        print()
        print(
            "SUMMARY_ROW "
            f"symbols={len(symbols)} "
            f"trials={len(all_results)} "
            f"signal_candidates="
            f"{len(candidates)}"
        )

        print("gross_signal_edge_search=1")
        print("parameter_search_performed=0")
        print("economic_edge_claimed=0")
        print("execution_instrument_used=0")
        print("execution_costs_used=0")
        print("signal_metric_source=GROSS_PNL")
        print("purged_oos_used=1")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if candidates:
            verdict = (
                "UNIVERSE_TREND_PULLBACK_"
                "TRUE_GROSS_CANDIDATES_FOUND"
            )
        else:
            verdict = (
                "UNIVERSE_TREND_PULLBACK_"
                "TRUE_GROSS_NO_CANDIDATES"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
