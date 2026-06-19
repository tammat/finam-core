#!/usr/bin/env python3
from __future__ import annotations

import os
from statistics import mean
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_GUARD_THRESHOLD_AUDIT_V1
# Read-only аудит порогов pre-signal guard для equity.
# Проверяет, являются ли br_volatility_too_low/compression_watch_active
# только плохим названием или реально неподходящим guard для акции.


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
STRATEGY = os.getenv("EQUITY_EXPECTED_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
LOOKBACK_DAYS = int(os.getenv("EQUITY_GUARD_THRESHOLD_LOOKBACK_DAYS", "30"))

TABLE = "runtime_guard_pre_signal_block_audit_v1"


def fnum(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


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

    interval = f"{LOOKBACK_DAYS} days"

    print("=== EQUITY GUARD THRESHOLD AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if not table_exists(cur, TABLE):
                print("EQUITY_GUARD_THRESHOLD_AUDIT_SUMMARY")
                print("guard_table_exists=0")
                print("VERDICT=EQUITY_GUARD_THRESHOLD_TABLE_MISSING")
                print("EQUITY_GUARD_THRESHOLD_AUDIT_V1_OK")
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
                    block_reason,
                    block_type,
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
                """,
                (SYMBOL, STRATEGY, interval),
            )
            rows = list(cur.fetchall())

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        reason = sval(row.get("block_reason"))
        groups.setdefault(reason, []).append(row)

    print("EQUITY_GUARD_THRESHOLD_REASON_ROWS")
    for reason, rs in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
        atr_pcts = [fnum(r.get("atr_pct")) for r in rs if fnum(r.get("atr_pct")) is not None]
        thresholds = [fnum(r.get("threshold")) for r in rs if fnum(r.get("threshold")) is not None]
        compressions = [fnum(r.get("compression_ratio")) for r in rs if fnum(r.get("compression_ratio")) is not None]
        prices = [fnum(r.get("price")) for r in rs if fnum(r.get("price")) is not None]

        def fmt(values: list[float]) -> str:
            if not values:
                return "NULL"
            return f"min={min(values):.8f},avg={mean(values):.8f},max={max(values):.8f}"

        print(
            "EQUITY_GUARD_THRESHOLD_REASON_ROW "
            f"reason={reason} "
            f"rows={len(rs)} "
            f"atr_pct_stats={fmt(atr_pcts)} "
            f"threshold_stats={fmt(thresholds)} "
            f"compression_ratio_stats={fmt(compressions)} "
            f"price_stats={fmt(prices)}"
        )

    print()
    print("EQUITY_GUARD_THRESHOLD_SAMPLE_ROWS")
    for row in rows[:80]:
        payload = row.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        print(
            "EQUITY_GUARD_THRESHOLD_SAMPLE_ROW "
            f"id={row.get('id')} "
            f"created_at={row.get('created_at')} "
            f"reason={sval(row.get('block_reason'))} "
            f"block_type={sval(row.get('block_type'))} "
            f"timeframe={sval(row.get('timeframe'))} "
            f"price={row.get('price')} "
            f"atr={row.get('atr')} "
            f"atr_pct={row.get('atr_pct')} "
            f"threshold={row.get('threshold')} "
            f"compression_ratio={row.get('compression_ratio')} "
            f"volatility={sval(row.get('volatility'))} "
            f"trend={sval(row.get('trend'))} "
            f"regime={sval(row.get('regime'))} "
            f"vol_gate_mode={sval(payload.get('vol_gate_mode'), 'NULL')} "
            f"static_threshold={sval(payload.get('static_threshold'), 'NULL')}"
        )

    total_rows = len(rows)
    br_low_rows = len(groups.get("br_volatility_too_low", []))
    compression_rows = len(groups.get("compression_watch_active", []))

    atr_pct_values = [fnum(r.get("atr_pct")) for r in rows if fnum(r.get("atr_pct")) is not None]
    threshold_values = [fnum(r.get("threshold")) for r in rows if fnum(r.get("threshold")) is not None]

    avg_atr_pct = mean(atr_pct_values) if atr_pct_values else None
    avg_threshold = mean(threshold_values) if threshold_values else None

    print()
    print("EQUITY_GUARD_THRESHOLD_AUDIT_SUMMARY")
    print("guard_table_exists=1")
    print(f"guard_rows_total={total_rows}")
    print(f"br_volatility_too_low_rows={br_low_rows}")
    print(f"compression_watch_active_rows={compression_rows}")
    print(f"avg_atr_pct={'NULL' if avg_atr_pct is None else f'{avg_atr_pct:.8f}'}")
    print(f"avg_threshold={'NULL' if avg_threshold is None else f'{avg_threshold:.8f}'}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if total_rows == 0:
        print("VERDICT=EQUITY_GUARD_THRESHOLD_NO_ROWS")
    elif br_low_rows > 0 and avg_atr_pct is not None and avg_threshold is not None and avg_atr_pct < avg_threshold:
        print("VERDICT=EQUITY_LOW_VOL_BLOCK_NUMERICALLY_CONFIRMED")
    elif br_low_rows > 0:
        print("VERDICT=EQUITY_BR_NAMED_REASON_REVIEW_REQUIRED")
    elif compression_rows > 0:
        print("VERDICT=EQUITY_COMPRESSION_BLOCK_REVIEW_REQUIRED")
    else:
        print("VERDICT=EQUITY_GUARD_THRESHOLD_REVIEW_REQUIRED")

    print("EQUITY_GUARD_THRESHOLD_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
