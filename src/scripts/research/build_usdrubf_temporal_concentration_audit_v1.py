#!/usr/bin/env python3
"""
USDRUBF_TEMPORAL_CONCENTRATION_AUDIT_V1

Read-only forensic.

Проверяет, насколько gross PnL шести preliminary USDRUBF
кандидатов сконцентрирован в отдельных временных folds.

Не ищет новые параметры.
Не использует costs.
Не пишет в PostgreSQL.
"""

from __future__ import annotations

import json
import math
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

SYMBOL = "USDRUBF@RTSX"
TIMEFRAME = "M5"
FOLD_COUNT = 3

STRATEGY_CODES = {
    "MOMENTUM": "MOMENTUM_CONTINUATION_V2",
    "BREAKOUT": "VOLATILITY_BREAKOUT_V2",
}


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def trade_pnl(trade) -> Decimal:
    for field in ("gross_pnl", "net_pnl", "pnl"):
        value = getattr(trade, field, None)

        if value is not None:
            return Decimal(str(value))

    return Decimal("0")


def main() -> int:
    cfg = json.loads(CONFIG_PATH.read_text())

    print("=== USDRUBF TEMPORAL CONCENTRATION AUDIT V1 ===")
    print("mode=read_only_temporal_forensic")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("parameter_search_performed=0")
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
                (SYMBOL, TIMEFRAME),
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
            * float(cfg["development_fraction"])
        )

        candidate_count = 0
        concentrated_count = 0

        for family in ("MOMENTUM", "BREAKOUT"):

            strategy_code = STRATEGY_CODES[family]

            for variant_no, raw_params in enumerate(
                cfg["families"][family],
                start=1,
            ):
                params = dict(raw_params)
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
                    - int(params["lookback"]),
                )

                generated = build_trades(
                    {
                        "strategy_code": strategy_code,
                        "parameter_json": params,
                    },
                    bars[source_start:],
                )

                oos = trades_in_purged_window(
                    generated,
                    start_ts=oos_start,
                    end_ts=oos_stop,
                )

                result = metrics(oos)

                trades_count = int(
                    result.get("trades") or 0
                )
                pf = dec(
                    result.get("profit_factor")
                )
                expectancy = dec(
                    result.get("expectancy")
                )

                preliminary = (
                    trades_count
                    >= int(cfg["minimum_oos_trades"])
                    and pf
                    >= dec(
                        cfg[
                            "minimum_oos_profit_factor"
                        ]
                    )
                    and expectancy > 0
                )

                if not preliminary:
                    continue

                candidate_count += 1

                ordered = sorted(
                    oos,
                    key=lambda trade: trade.entry_ts,
                )

                fold_size = math.ceil(
                    len(ordered) / FOLD_COUNT
                )

                fold_rows = []

                for fold_no in range(FOLD_COUNT):
                    start = fold_no * fold_size
                    stop = min(
                        (fold_no + 1) * fold_size,
                        len(ordered),
                    )

                    sample = ordered[start:stop]

                    if not sample:
                        continue

                    fold_metrics = metrics(sample)

                    pnl = sum(
                        (
                            trade_pnl(trade)
                            for trade in sample
                        ),
                        Decimal("0"),
                    )

                    fold_rows.append({
                        "fold": fold_no + 1,
                        "start_ts": sample[0].entry_ts,
                        "end_ts": sample[-1].entry_ts,
                        "trades": len(sample),
                        "pnl": pnl,
                        "pf": dec(
                            fold_metrics.get(
                                "profit_factor"
                            )
                        ),
                        "expectancy": dec(
                            fold_metrics.get(
                                "expectancy"
                            )
                        ),
                    })

                total_abs_pnl = sum(
                    (
                        abs(row["pnl"])
                        for row in fold_rows
                    ),
                    Decimal("0"),
                )

                max_abs_share = Decimal("0")

                if total_abs_pnl > 0:
                    max_abs_share = max(
                        abs(row["pnl"])
                        / total_abs_pnl
                        for row in fold_rows
                    )

                concentrated = (
                    max_abs_share
                    >= Decimal("0.70")
                )

                if concentrated:
                    concentrated_count += 1

                print(
                    "CANDIDATE_CONCENTRATION_ROW "
                    f"family={family} "
                    f"strategy={strategy_code} "
                    f"variant={variant_no} "
                    f"oos_trades={trades_count} "
                    f"oos_profit_factor={pf} "
                    f"oos_expectancy={expectancy} "
                    f"max_abs_fold_pnl_share="
                    f"{max_abs_share:.6f} "
                    f"temporally_concentrated="
                    f"{int(concentrated)}"
                )

                for row in fold_rows:
                    print(
                        "TEMPORAL_FOLD_ROW "
                        f"family={family} "
                        f"variant={variant_no} "
                        f"fold={row['fold']} "
                        f"start_ts={row['start_ts']} "
                        f"end_ts={row['end_ts']} "
                        f"trades={row['trades']} "
                        f"gross_pnl={row['pnl']} "
                        f"profit_factor={row['pf']} "
                        f"expectancy="
                        f"{row['expectancy']}"
                    )

        print()
        print(
            "SUMMARY_ROW "
            f"preliminary_candidates="
            f"{candidate_count} "
            f"temporally_concentrated="
            f"{concentrated_count}"
        )

        print("parameter_search_performed=0")
        print("economic_edge_claimed=0")
        print("execution_costs_used=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if concentrated_count:
            verdict = (
                "USDRUBF_TEMPORAL_CONCENTRATION_"
                "DETECTED"
            )
        else:
            verdict = (
                "USDRUBF_TEMPORAL_CONCENTRATION_"
                "NOT_DETECTED"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
