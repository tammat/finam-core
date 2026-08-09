#!/usr/bin/env python3
"""
IMOEX2_MXU6_SIGNAL_REPLAY_CONTRACT_V1

Цель:
- получить реальные trades существующего canonical strategy runner;
- определить фактический trade contract;
- проверить возможность timestamp-alignment IMOEX2 -> MXU6;
- ничего не оценивать экономически;
- ничего не писать в PostgreSQL.
"""

from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import (
    Bar,
    build_trades,
)


SIGNAL_SYMBOL = "IMOEX2"
EXECUTION_SYMBOL = "MXU6@RTSX"
TIMEFRAME = "M5"

RUN = {
    "strategy_code": "MOMENTUM_CONTINUATION_V2",
    "parameter_json": {
        "lookback": 20,
        "hold": 5,
        "threshold": 0.5,
        # Контракт-аудит: economics intentionally disabled.
        "commission": 0.0,
        "slippage": 0.0,
    },
}


def public_trade_shape(trade) -> dict:
    if isinstance(trade, dict):
        return dict(trade)

    if hasattr(trade, "__dict__"):
        return {
            key: value
            for key, value in vars(trade).items()
            if not key.startswith("_")
        }

    fields = {}

    for name in (
        "entry_ts",
        "exit_ts",
        "side",
        "direction",
        "entry_price",
        "exit_price",
        "pnl",
    ):
        if hasattr(trade, name):
            fields[name] = getattr(trade, name)

    return fields


def main() -> int:
    print("=== IMOEX2 MXU6 SIGNAL REPLAY CONTRACT V1 ===")
    print("mode=research_read_only")
    print(f"signal_symbol={SIGNAL_SYMBOL}")
    print(f"execution_symbol={EXECUTION_SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("economic_verdict_allowed=0")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            # Ограничиваемся периодом существования MXU6 M5.
            cur.execute(
                """
                SELECT min(ts) AS first_ts, max(ts) AS last_ts
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                """,
                (EXECUTION_SYMBOL, TIMEFRAME),
            )

            execution_range = dict(cur.fetchone() or {})

            first_ts = execution_range.get("first_ts")
            last_ts = execution_range.get("last_ts")

            if first_ts is None or last_ts is None:
                print("VERDICT=IMOEX2_MXU6_SIGNAL_REPLAY_NO_EXECUTION_RANGE")
                return 3

            cur.execute(
                """
                SELECT ts,close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND ts BETWEEN %s AND %s
                  AND close IS NOT NULL
                ORDER BY ts
                """,
                (
                    SIGNAL_SYMBOL,
                    TIMEFRAME,
                    first_ts,
                    last_ts,
                ),
            )

            signal_bars = [
                Bar(row["ts"], float(row["close"]))
                for row in cur.fetchall()
            ]

            cur.execute(
                """
                SELECT ts,close
                FROM public.market_bars
                WHERE symbol=%s
                  AND timeframe=%s
                  AND ts BETWEEN %s AND %s
                  AND close IS NOT NULL
                ORDER BY ts
                """,
                (
                    EXECUTION_SYMBOL,
                    TIMEFRAME,
                    first_ts,
                    last_ts,
                ),
            )

            execution_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

        trades = build_trades(
            RUN,
            signal_bars,
        )

        print(
            "RANGE_ROW "
            f"first_ts={first_ts} "
            f"last_ts={last_ts}"
        )

        print(
            "BAR_ROW "
            f"signal_bars={len(signal_bars)} "
            f"execution_bars={len(execution_rows)}"
        )

        print(f"TRADE_ROW trades={len(trades)}")

        if not trades:
            print("trade_contract_detected=0")
            print("timestamp_contract_detected=0")
            print("db_writes_performed=0")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("micro_live_allowed=0")
            print(
                "VERDICT="
                "IMOEX2_MXU6_SIGNAL_REPLAY_NO_SAMPLE_TRADES"
            )
            return 0

        shape = public_trade_shape(trades[0])

        keys = sorted(shape)

        print(
            "TRADE_CONTRACT_ROW "
            f"type={type(trades[0]).__name__} "
            f"fields={','.join(keys)}"
        )

        for key in keys:
            print(
                "TRADE_FIELD "
                f"name={key} "
                f"value={shape[key]}"
            )

        timestamp_candidates = {
            "entry_ts",
            "exit_ts",
        }

        timestamp_contract = (
            timestamp_candidates.issubset(shape.keys())
        )

        execution_ts = {
            row["ts"]
            for row in execution_rows
        }

        aligned = 0
        checked = 0

        if timestamp_contract:
            for trade in trades:
                current = public_trade_shape(trade)

                entry_ts = current.get("entry_ts")
                exit_ts = current.get("exit_ts")

                if entry_ts is None or exit_ts is None:
                    continue

                checked += 1

                if (
                    entry_ts in execution_ts
                    and exit_ts in execution_ts
                ):
                    aligned += 1

        alignment_ratio = (
            aligned / checked
            if checked
            else 0.0
        )

        print()
        print(
            f"trade_contract_detected={int(bool(shape))}"
        )
        print(
            f"timestamp_contract_detected="
            f"{int(timestamp_contract)}"
        )
        print(
            "TIMESTAMP_ALIGNMENT_ROW "
            f"checked={checked} "
            f"aligned={aligned} "
            f"ratio={alignment_ratio:.6f}"
        )

        print("economic_verdict_allowed=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if (
            timestamp_contract
            and checked > 0
            and alignment_ratio >= 0.90
        ):
            verdict = (
                "IMOEX2_MXU6_SIGNAL_REPLAY_CONTRACT_READY"
            )
        elif timestamp_contract:
            verdict = (
                "IMOEX2_MXU6_SIGNAL_REPLAY_ALIGNMENT_INSUFFICIENT"
            )
        else:
            verdict = (
                "IMOEX2_MXU6_SIGNAL_REPLAY_TRADE_CONTRACT_REVIEW"
            )

        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
