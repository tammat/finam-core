#!/usr/bin/env python3
"""
UNIVERSE_SIGNAL_EXECUTION_COST_CONTRACT_AUDIT_V1

Read-only forensic.

Проверяет, действительно ли gross signal screen работает
без execution economics.

Никаких записей в PostgreSQL.
Никаких orders/fills/runtime changes.
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

SYMBOL = "USDRUBF@RTSX"
TIMEFRAME = "M5"
STRATEGY_CODE = "MOMENTUM_CONTINUATION_V2"
VARIANT_INDEX = 1  # variant=2


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def main() -> int:
    cfg = json.loads(CONFIG_PATH.read_text())

    raw = cfg["families"]["MOMENTUM"][VARIANT_INDEX]

    params = dict(raw)
    params["commission"] = 0.0
    params["slippage"] = 0.0

    print(
        "=== UNIVERSE SIGNAL EXECUTION "
        "COST CONTRACT AUDIT V1 ==="
    )
    print("mode=read_only_contract_audit")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY_CODE}")
    print("requested_commission=0")
    print("requested_slippage=0")

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

        oos_start, oos_stop, _ = purged_bar_window(
            bars,
            start=development_end,
            end=len(bars),
            parameters=params,
        )

        source_start = max(
            0,
            development_end - int(params["lookback"]),
        )

        generated = build_trades(
            {
                "strategy_code": STRATEGY_CODE,
                "parameter_json": params,
            },
            bars[source_start:],
        )

        trades = trades_in_purged_window(
            generated,
            start_ts=oos_start,
            end_ts=oos_stop,
        )

        gross_total = sum(
            (dec(t.gross_pnl) for t in trades),
            Decimal("0"),
        )

        commission_total = sum(
            (dec(t.commission) for t in trades),
            Decimal("0"),
        )

        slippage_total = sum(
            (dec(t.slippage) for t in trades),
            Decimal("0"),
        )

        net_total = sum(
            (dec(t.net_pnl) for t in trades),
            Decimal("0"),
        )

        gross_net_gap = gross_total - net_total

        nonzero_commission = sum(
            1
            for t in trades
            if dec(t.commission) != 0
        )

        nonzero_slippage = sum(
            1
            for t in trades
            if dec(t.slippage) != 0
        )

        off_grid_entry = sum(
            1
            for t in trades
            if (
                t.entry_ts.second != 0
                or t.entry_ts.microsecond != 0
                or t.entry_ts.minute % 5 != 0
            )
        )

        off_grid_exit = sum(
            1
            for t in trades
            if (
                t.exit_ts.second != 0
                or t.exit_ts.microsecond != 0
                or t.exit_ts.minute % 5 != 0
            )
        )

        result = metrics(trades)

        print(
            "PNL_CONTRACT_ROW "
            f"trades={len(trades)} "
            f"gross_total={gross_total} "
            f"commission_total={commission_total} "
            f"slippage_total={slippage_total} "
            f"net_total={net_total} "
            f"gross_net_gap={gross_net_gap}"
        )

        print(
            "COST_CONTRACT_ROW "
            f"nonzero_commission_trades="
            f"{nonzero_commission} "
            f"nonzero_slippage_trades="
            f"{nonzero_slippage}"
        )

        print(
            "TIMESTAMP_CONTRACT_ROW "
            f"off_grid_entry={off_grid_entry} "
            f"off_grid_exit={off_grid_exit}"
        )

        print(
            "METRICS_ROW "
            f"profit_factor="
            f"{result.get('profit_factor')} "
            f"expectancy="
            f"{result.get('expectancy')}"
        )

        hidden_costs = (
            commission_total != 0
            or slippage_total != 0
            or gross_net_gap != 0
        )

        print(
            f"hidden_execution_costs_detected="
            f"{int(hidden_costs)}"
        )

        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if hidden_costs:
            verdict = (
                "UNIVERSE_SIGNAL_SCREEN_"
                "EXECUTION_COST_CONTAMINATION_DETECTED"
            )
        else:
            verdict = (
                "UNIVERSE_SIGNAL_SCREEN_"
                "GROSS_CONTRACT_CONFIRMED"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
