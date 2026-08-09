#!/usr/bin/env python3

from __future__ import annotations

import os
import statistics

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


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SYMBOL = os.getenv("BR_DISCOVERY_SYMBOL", "BRU6@RTSX")
TIMEFRAME = "M5"

FAMILIES = (
    (
        "MOMENTUM",
        "MOMENTUM_CONTINUATION_V2",
        [
            {"lookback": 10, "hold": 5, "threshold": 0.25},
            {"lookback": 20, "hold": 5, "threshold": 0.50},
            {"lookback": 40, "hold": 10, "threshold": 1.00},
        ],
    ),
    (
        "MEAN_REVERSION",
        "MEAN_REVERSION_V2",
        [
            {"lookback": 10, "hold": 5, "threshold": 1.0},
            {"lookback": 20, "hold": 5, "threshold": 1.5},
            {"lookback": 40, "hold": 10, "threshold": 2.0},
        ],
    ),
)


def main() -> int:
    print("=== BR NEW STRATEGY FAMILY DISCOVERY V1 ===")
    print("mode=research_read_only")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("excluded_strategy=BR_CONSERVATIVE_BREAKOUT")
    print("families=MOMENTUM,MEAN_REVERSION")
    print("runtime_changed=0")
    print("execution_changed=0")
    print()

    conn = psycopg2.connect(DB)
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT ts, close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                ORDER BY ts
                """,
                (SYMBOL, TIMEFRAME),
            )

            bars = [
                Bar(row["ts"], float(row["close"]))
                for row in cur.fetchall()
                if row["close"] is not None
            ]

        print(f"bars={len(bars)}")

        if len(bars) < 1000:
            print("VERDICT=BR_NEW_FAMILY_DISCOVERY_INSUFFICIENT_BARS")
            return 3

        validation_end = int(len(bars) * 0.75)

        # Пока только research comparison.
        # Cost-model intentionally not asserted as production-realistic.
        reference_price = statistics.median(
            bar.close for bar in bars
        )

        commission = reference_price * 8.0 / 10000.0

        print(
            "cost_model=RESEARCH_8BPS_COMMISSION_SLIPPAGE_ZERO"
        )
        print(f"commission_per_trade_proxy={commission:.8f}")
        print()

        results = []

        for family, strategy_code, parameter_sets in FAMILIES:
            for index, base_params in enumerate(
                parameter_sets,
                start=1,
            ):
                params = {
                    **base_params,
                    "commission": commission,
                    "slippage": 0.0,
                }

                lookback = int(params["lookback"])

                oos_start, oos_stop, _ = purged_bar_window(
                    bars,
                    start=validation_end,
                    end=len(bars),
                    parameters=params,
                )

                run = {
                    "strategy_code": strategy_code,
                    "parameter_json": params,
                }

                all_trades = build_trades(
                    run,
                    bars[validation_end - lookback :],
                )

                oos_trades = trades_in_purged_window(
                    all_trades,
                    start_ts=oos_start,
                    end_ts=oos_stop,
                )

                result = metrics(oos_trades)

                print(
                    "DISCOVERY_ROW "
                    f"family={family} "
                    f"strategy={strategy_code} "
                    f"variant={index} "
                    f"lookback={params['lookback']} "
                    f"hold={params['hold']} "
                    f"threshold={params['threshold']} "
                    f"trades={result['trades']} "
                    f"profit_factor={result['profit_factor']} "
                    f"expectancy={result['expectancy']}"
                )

                results.append(
                    (
                        family,
                        strategy_code,
                        index,
                        result,
                    )
                )

        positive = [
            row
            for row in results
            if row[3]["trades"] >= 30
            and row[3]["profit_factor"] >= 1.10
            and row[3]["expectancy"] > 0
        ]

        print()
        print(
            "SUMMARY_ROW "
            f"variants={len(results)} "
            f"positive_candidates={len(positive)}"
        )
        print("db_writes_performed=0")
        print("runtime_allow=0")
        print("execution_enabled=0")

        if positive:
            print(
                "VERDICT="
                "BR_NEW_STRATEGY_FAMILY_DISCOVERY_CANDIDATES_FOUND"
            )
        else:
            print(
                "VERDICT="
                "BR_NEW_STRATEGY_FAMILY_DISCOVERY_NO_CANDIDATES"
            )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
