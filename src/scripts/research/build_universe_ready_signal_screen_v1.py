#!/usr/bin/env python3
"""
UNIVERSE_READY_SIGNAL_SCREEN_V1

Gross signal screen новых RESEARCH_READY инструментов.

Контракт:
- predefined variants;
- chronological + purged OOS;
- commission=0;
- slippage=0;
- PostgreSQL read-only;
- никаких execution/economic claims.
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


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")

    return Decimal(str(value))


def main() -> int:
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    symbols = list(cfg["symbols"])
    timeframe = cfg["timeframe"]

    print("=== UNIVERSE READY SIGNAL SCREEN V1 ===")
    print("mode=gross_signal_screen")
    print(f"timeframe={timeframe}")
    print(f"symbols={len(symbols)}")
    print("execution_instrument_used=0")
    print("execution_costs_used=0")
    print("commission=0")
    print("slippage=0")
    print()

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        results = []
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

                total_bars = len(bars)

                print(
                    "SYMBOL_ROW "
                    f"symbol={symbol} "
                    f"bars={total_bars}"
                )

                if total_bars < int(
                    cfg["minimum_bars"]
                ):
                    print(
                        "SYMBOL_SKIP "
                        f"symbol={symbol} "
                        "reason=INSUFFICIENT_BARS"
                    )
                    continue

                development_end = int(
                    total_bars
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

                    for (
                        variant_no,
                        raw_params,
                    ) in enumerate(
                        variants,
                        start=1,
                    ):

                        params = dict(
                            raw_params
                        )

                        params[
                            "commission"
                        ] = 0.0

                        params[
                            "slippage"
                        ] = 0.0

                        oos_start, oos_stop, _ = (
                            purged_bar_window(
                                bars,
                                start=development_end,
                                end=total_bars,
                                parameters=params,
                            )
                        )

                        source_start = max(
                            0,
                            development_end
                            - int(
                                params[
                                    "lookback"
                                ]
                            ),
                        )

                        run = {
                            "strategy_code":
                                strategy_code,
                            "parameter_json":
                                params,
                        }

                        generated = build_trades(
                            run,
                            bars[source_start:],
                        )

                        oos_trades = (
                            trades_in_purged_window(
                                generated,
                                start_ts=oos_start,
                                end_ts=oos_stop,
                            )
                        )

                        metric = metrics(
                            oos_trades
                        )

                        trade_count = int(
                            metric.get(
                                "trades"
                            )
                            or 0
                        )

                        pf = dec(
                            metric.get(
                                "profit_factor"
                            )
                        )

                        expectancy = dec(
                            metric.get(
                                "expectancy"
                            )
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
                            "symbol":
                                symbol,
                            "family":
                                family,
                            "strategy":
                                strategy_code,
                            "variant":
                                variant_no,
                            "trades":
                                trade_count,
                            "pf":
                                pf,
                            "expectancy":
                                expectancy,
                            "candidate":
                                candidate,
                        }

                        results.append(row)

                        if candidate:
                            candidates.append(
                                row
                            )

                        print(
                            "SCREEN_ROW "
                            f"symbol={symbol} "
                            f"family={family} "
                            f"strategy="
                            f"{strategy_code} "
                            f"variant="
                            f"{variant_no} "
                            f"oos_trades="
                            f"{trade_count} "
                            "gross_oos_profit_factor="
                            f"{pf} "
                            "gross_oos_expectancy="
                            f"{expectancy} "
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
                f"family={row['family']} "
                f"strategy={row['strategy']} "
                f"variant={row['variant']} "
                f"oos_trades={row['trades']} "
                "gross_oos_profit_factor="
                f"{row['pf']} "
                "gross_oos_expectancy="
                f"{row['expectancy']}"
            )

        print()
        print(
            "SUMMARY_ROW "
            f"symbols={len(symbols)} "
            f"trials={len(results)} "
            "signal_candidates="
            f"{len(candidates)}"
        )

        print("gross_signal_edge_search=1")
        print("economic_edge_claimed=0")
        print("execution_instrument_used=0")
        print("execution_costs_used=0")
        print("purged_oos_used=1")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if candidates:
            verdict = (
                "UNIVERSE_READY_SIGNAL_"
                "CANDIDATES_FOUND"
            )
        else:
            verdict = (
                "UNIVERSE_READY_SIGNAL_"
                "NO_CANDIDATES"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
