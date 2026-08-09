#!/usr/bin/env python3
"""
IMOEX2_MULTI_FAMILY_DISCOVERY_V1

Цель:
найти или отвергнуть GROSS SIGNAL EDGE на IMOEX2.

Это НЕ execution backtest.

Принципы:
- только IMOEX2;
- commission=0;
- slippage=0;
- никаких MXU6 costs;
- chronological development/OOS split;
- purged OOS;
- несколько независимых strategy families;
- PostgreSQL read-only;
- runtime/execution не изменяются.

Если signal candidate найден:
следующий этап отдельно проверяет его исполнимость на MXU6.
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
    "config/research/imoex2_multi_family_discovery_v1.json"
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


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def main() -> int:
    cfg = load_config()

    symbol = cfg["symbol"]
    timeframe = cfg["timeframe"]

    minimum_trades = int(
        cfg["minimum_oos_trades"]
    )
    minimum_pf = dec(
        cfg["minimum_oos_profit_factor"]
    )
    minimum_expectancy = dec(
        cfg["minimum_oos_expectancy"]
    )

    print("=== IMOEX2 MULTI FAMILY DISCOVERY V1 ===")
    print("mode=gross_signal_edge_discovery")
    print(f"signal_symbol={symbol}")
    print(f"timeframe={timeframe}")
    print(
        "families="
        + ",".join(cfg["families"].keys())
    )
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
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT ts,close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND close IS NOT NULL
                ORDER BY ts
                """,
                (symbol, timeframe),
            )

            bars = [
                Bar(
                    row["ts"],
                    float(row["close"]),
                )
                for row in cur.fetchall()
            ]

        total_bars = len(bars)

        print(f"bars={total_bars}")

        if total_bars < int(cfg["minimum_bars"]):
            print(
                "VERDICT="
                "IMOEX2_SIGNAL_EDGE_INSUFFICIENT_BARS"
            )
            return 3

        development_end = int(
            total_bars
            * float(cfg["development_fraction"])
        )

        print(
            f"development_bars={development_end}"
        )
        print(
            f"raw_oos_bars="
            f"{total_bars - development_end}"
        )

        print()
        print("DISCOVERY_ROWS")

        results = []

        for family, variants in cfg["families"].items():

            strategy_code = STRATEGY_CODES[family]

            for variant_no, raw_params in enumerate(
                variants,
                start=1,
            ):
                params = dict(raw_params)

                # Gross signal discovery:
                # никаких execution costs.
                params["commission"] = 0.0
                params["slippage"] = 0.0

                lookback = int(params["lookback"])

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
                    development_end - lookback,
                )

                run = {
                    "strategy_code": strategy_code,
                    "parameter_json": params,
                }

                all_trades = build_trades(
                    run,
                    bars[source_start:],
                )

                oos_trades = trades_in_purged_window(
                    all_trades,
                    start_ts=oos_start,
                    end_ts=oos_stop,
                )

                result = metrics(oos_trades)

                trades = int(
                    result.get("trades") or 0
                )
                pf = dec(
                    result.get("profit_factor")
                )
                expectancy = dec(
                    result.get("expectancy")
                )

                candidate = (
                    trades >= minimum_trades
                    and pf >= minimum_pf
                    and expectancy > minimum_expectancy
                )

                row = {
                    "family": family,
                    "strategy": strategy_code,
                    "variant": variant_no,
                    "lookback": raw_params["lookback"],
                    "hold": raw_params["hold"],
                    "threshold": raw_params["threshold"],
                    "trades": trades,
                    "pf": pf,
                    "expectancy": expectancy,
                    "candidate": candidate,
                }

                results.append(row)

                print(
                    "DISCOVERY_ROW "
                    f"family={family} "
                    f"strategy={strategy_code} "
                    f"variant={variant_no} "
                    f"lookback={row['lookback']} "
                    f"hold={row['hold']} "
                    f"threshold={row['threshold']} "
                    f"oos_trades={trades} "
                    f"gross_oos_profit_factor={pf} "
                    f"gross_oos_expectancy={expectancy} "
                    f"signal_candidate={int(candidate)}"
                )

        candidates = [
            row
            for row in results
            if row["candidate"]
        ]

        ranked = sorted(
            candidates,
            key=lambda row: (
                row["expectancy"],
                row["pf"],
                row["trades"],
            ),
            reverse=True,
        )

        print()
        print("SIGNAL_CANDIDATE_ROWS")

        for rank, row in enumerate(
            ranked,
            start=1,
        ):
            print(
                "SIGNAL_CANDIDATE_ROW "
                f"rank={rank} "
                f"family={row['family']} "
                f"strategy={row['strategy']} "
                f"variant={row['variant']} "
                f"oos_trades={row['trades']} "
                f"gross_oos_profit_factor={row['pf']} "
                f"gross_oos_expectancy={row['expectancy']}"
            )

        print()
        print(
            "SUMMARY_ROW "
            f"variants={len(results)} "
            f"signal_candidates={len(candidates)}"
        )

        print("gross_signal_edge_search=1")
        print("economic_edge_claimed=0")
        print("execution_replay_required_for_promotion=1")
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
                "IMOEX2_GROSS_SIGNAL_"
                "CANDIDATES_FOUND"
            )
        else:
            verdict = (
                "IMOEX2_GROSS_SIGNAL_"
                "NO_CANDIDATES"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
