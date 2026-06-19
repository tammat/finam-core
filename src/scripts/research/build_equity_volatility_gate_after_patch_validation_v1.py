#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_VOLATILITY_GATE_AFTER_PATCH_VALIDATION_V1
# Read-only проверка после split patch:
# - свежие SBER@MISX guard rows должны использовать equity_volatility_too_low;
# - threshold должен быть equity threshold, по умолчанию 0.0005;
# - старые br_volatility_too_low после restart недопустимы для @MISX.


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
STRATEGY = os.getenv("EQUITY_EXPECTED_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
LOOKBACK_MINUTES = int(os.getenv("EQUITY_AFTER_PATCH_LOOKBACK_MINUTES", "120"))
EXPECTED_THRESHOLD = float(os.getenv("EQUITY_ATR_MIN_PCT", "0.0005"))

TABLE = "runtime_guard_pre_signal_block_audit_v1"


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def fnum(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def table_exists(cur, table: str) -> bool:
    cur.execute(
        """
        select exists (
            select 1
            from information_schema.tables
            where table_schema = 'public'
              and table_name = %s
        )
        """,
        (table,),
    )
    return bool(cur.fetchone()[0])


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_MINUTES} minutes"

    print("=== EQUITY VOLATILITY GATE AFTER PATCH VALIDATION V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"lookback_minutes={LOOKBACK_MINUTES}")
    print(f"expected_equity_threshold={EXPECTED_THRESHOLD:.8f}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if not table_exists(cur, TABLE):
                print("EQUITY_VOLATILITY_GATE_AFTER_PATCH_SUMMARY")
                print("guard_table_exists=0")
                print("VERDICT=EQUITY_AFTER_PATCH_GUARD_TABLE_MISSING")
                print("EQUITY_VOLATILITY_GATE_AFTER_PATCH_VALIDATION_V1_OK")
                return 0

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""
                select
                    id,
                    created_at,
                    ts,
                    symbol,
                    strategy,
                    timeframe,
                    block_type,
                    block_reason,
                    price,
                    atr,
                    atr_pct,
                    threshold,
                    compression_ratio,
                    volatility,
                    trend,
                    regime,
                    payload
                from {TABLE}
                where symbol = %s
                  and strategy = %s
                  and created_at >= now() - (%s::text)::interval
                order by created_at desc, id desc
                limit 100
                """,
                (SYMBOL, STRATEGY, interval),
            )
            rows = list(cur.fetchall())

            cur.execute(
                """
                select count(*) as signals
                from signals
                where symbol = %s
                  and created_at >= now() - (%s::text)::interval
                """,
                (SYMBOL, interval),
            )
            signal_count = int(cur.fetchone()["signals"])

    print("EQUITY_AFTER_PATCH_GUARD_ROWS")
    br_reason_rows = 0
    equity_reason_rows = 0
    expected_threshold_rows = 0
    wrong_threshold_rows = 0
    compression_rows = 0

    for r in rows:
        reason = sval(r.get("block_reason"))
        block_type = sval(r.get("block_type"))
        threshold = fnum(r.get("threshold"))

        if reason == "br_volatility_too_low":
            br_reason_rows += 1
        if reason == "equity_volatility_too_low":
            equity_reason_rows += 1
        if block_type == "COMPRESSION_WATCH":
            compression_rows += 1

        if threshold is not None:
            if abs(threshold - EXPECTED_THRESHOLD) < 0.00000001:
                expected_threshold_rows += 1
            elif block_type == "VOL_LOW_BLOCK":
                wrong_threshold_rows += 1

        payload = r.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        print(
            "EQUITY_AFTER_PATCH_GUARD_ROW "
            f"id={r.get('id')} "
            f"created_at={r.get('created_at')} "
            f"symbol={r.get('symbol')} "
            f"strategy={r.get('strategy')} "
            f"timeframe={r.get('timeframe')} "
            f"block_type={block_type} "
            f"reason={reason} "
            f"price={r.get('price')} "
            f"atr={r.get('atr')} "
            f"atr_pct={r.get('atr_pct')} "
            f"threshold={r.get('threshold')} "
            f"compression_ratio={r.get('compression_ratio')} "
            f"volatility={sval(r.get('volatility'))} "
            f"trend={sval(r.get('trend'))} "
            f"vol_gate_mode={sval(payload.get('vol_gate_mode'), 'NULL')} "
            f"static_threshold={sval(payload.get('static_threshold'), 'NULL')}"
        )

    print()
    print("EQUITY_VOLATILITY_GATE_AFTER_PATCH_SUMMARY")
    print("guard_table_exists=1")
    print(f"fresh_guard_rows={len(rows)}")
    print(f"fresh_signals={signal_count}")
    print(f"equity_volatility_reason_rows={equity_reason_rows}")
    print(f"br_volatility_reason_rows={br_reason_rows}")
    print(f"expected_threshold_rows={expected_threshold_rows}")
    print(f"wrong_threshold_rows={wrong_threshold_rows}")
    print(f"compression_watch_rows={compression_rows}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if len(rows) == 0 and signal_count == 0:
        print("VERDICT=EQUITY_AFTER_PATCH_WAIT_FOR_FRESH_ROWS")
    elif br_reason_rows > 0 or wrong_threshold_rows > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_FAILED_BR_REASON_OR_THRESHOLD_STILL_USED")
    elif equity_reason_rows > 0 and expected_threshold_rows > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_OK_EQUITY_LOW_VOL_GUARD")
    elif signal_count > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_SIGNAL_FLOW_PROGRESS")
    elif compression_rows > 0:
        print("VERDICT=EQUITY_AFTER_PATCH_COMPRESSION_WATCH_NEXT_BLOCK")
    else:
        print("VERDICT=EQUITY_AFTER_PATCH_REVIEW_REQUIRED")

    print("EQUITY_VOLATILITY_GATE_AFTER_PATCH_VALIDATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
