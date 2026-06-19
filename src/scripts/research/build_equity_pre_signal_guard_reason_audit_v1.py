#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_V1
# Read-only аудит причин блокировки equity signals до emit.
# Фокус: SBER@MISX / VOLATILITY_BREAKOUT_EQUITY / причины br_volatility_too_low и compression_watch_active.


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
EXPECTED_STRATEGY = os.getenv("EQUITY_EXPECTED_STRATEGY", "VOLATILITY_BREAKOUT_EQUITY")
LOOKBACK_DAYS = int(os.getenv("EQUITY_PRE_SIGNAL_GUARD_LOOKBACK_DAYS", "30"))
SAMPLE_LIMIT = int(os.getenv("EQUITY_PRE_SIGNAL_GUARD_SAMPLE_LIMIT", "80"))

TABLE = "runtime_guard_pre_signal_block_audit_v1"


def sval(value: Any, default: str = "UNKNOWN") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


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


def columns(cur, table: str) -> set[str]:
    cur.execute(
        """
        select column_name
        from information_schema.columns
        where table_schema = 'public'
          and table_name = %s
        order by ordinal_position
        """,
        (table,),
    )
    result: set[str] = set()
    for row in cur.fetchall():
        if isinstance(row, dict):
            result.add(str(row["column_name"]))
        else:
            result.add(str(row[0]))
    return result


def first_col(cols: set[str], names: list[str]) -> str | None:
    for name in names:
        if name in cols:
            return name
    return None


def expr(cols: set[str], name: str, default: str = "NULL") -> str:
    if name in cols:
        return name
    return f"'{default}' as {name}"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== EQUITY PRE SIGNAL GUARD REASON AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"expected_strategy={EXPECTED_STRATEGY}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            if not table_exists(cur, TABLE):
                print("EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_SUMMARY")
                print("guard_table_exists=0")
                print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_TABLE_MISSING")
                print("EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_V1_OK")
                return 0

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cols = columns(cur, TABLE)
            ts_col = first_col(cols, ["created_at", "ts", "timestamp", "updated_at"])
            if not ts_col:
                raise SystemExit("NO_TIMESTAMP_COLUMN_IN_GUARD_TABLE")

            reason_col = first_col(cols, ["reason", "block_reason", "event_type", "status"])
            reason_expr = reason_col if reason_col else "'UNKNOWN' as reason"

            strategy_expr = "strategy" if "strategy" in cols else "'UNKNOWN' as strategy"
            timeframe_expr = "timeframe" if "timeframe" in cols else "'UNKNOWN' as timeframe"
            payload_expr = "payload" if "payload" in cols else "'{}'::jsonb as payload"
            features_expr = "features" if "features" in cols else "'{}'::jsonb as features"

            print("EQUITY_PRE_SIGNAL_GUARD_SCHEMA")
            print("EQUITY_PRE_SIGNAL_GUARD_SCHEMA_ROW columns=" + ",".join(sorted(cols)))
            print()

            cur.execute(
                f"""
                select
                    symbol,
                    coalesce({strategy_expr}, 'UNKNOWN') as strategy,
                    coalesce({timeframe_expr}, 'UNKNOWN') as timeframe,
                    coalesce({reason_expr}, 'UNKNOWN') as reason,
                    count(*) as rows,
                    min({ts_col}) as first_ts,
                    max({ts_col}) as last_ts
                from {TABLE}
                where symbol = %s
                  and {ts_col} >= now() - (%s::text)::interval
                group by 1,2,3,4
                order by rows desc, last_ts desc
                """,
                (SYMBOL, interval),
            )
            groups = list(cur.fetchall())

            cur.execute(
                f"""
                select
                    id,
                    {ts_col} as created_at,
                    symbol,
                    coalesce({strategy_expr}, 'UNKNOWN') as strategy,
                    coalesce({timeframe_expr}, 'UNKNOWN') as timeframe,
                    coalesce({reason_expr}, 'UNKNOWN') as reason,
                    {payload_expr},
                    {features_expr}
                from {TABLE}
                where symbol = %s
                  and {ts_col} >= now() - (%s::text)::interval
                order by {ts_col} desc, id desc
                limit %s
                """,
                (SYMBOL, interval, SAMPLE_LIMIT),
            )
            samples = list(cur.fetchall())

    print("EQUITY_PRE_SIGNAL_GUARD_GROUP_ROWS")
    total_rows = 0
    target_rows = 0
    br_named_reason_rows = 0

    for r in groups:
        rows = int(r["rows"])
        total_rows += rows

        strategy = sval(r["strategy"])
        reason = sval(r["reason"])

        if strategy == EXPECTED_STRATEGY:
            target_rows += rows

        if reason.startswith("br_") or "br_" in reason:
            br_named_reason_rows += rows

        print(
            "EQUITY_PRE_SIGNAL_GUARD_GROUP_ROW "
            f"symbol={r['symbol']} "
            f"strategy={strategy} "
            f"timeframe={sval(r['timeframe'])} "
            f"reason={reason} "
            f"rows={rows} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']} "
            f"is_expected_strategy={int(strategy == EXPECTED_STRATEGY)} "
            f"is_br_named_reason={int(reason.startswith('br_') or 'br_' in reason)}"
        )

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_SAMPLE_ROWS")

    for r in samples:
        payload = r.get("payload")
        features = r.get("features")

        if not isinstance(payload, dict):
            payload = {}
        if not isinstance(features, dict):
            features = {}

        payload_keys = ",".join(sorted(payload.keys())) if payload else "NO_PAYLOAD"
        feature_keys = ",".join(sorted(features.keys())) if features else "NO_FEATURES"

        print(
            "EQUITY_PRE_SIGNAL_GUARD_SAMPLE_ROW "
            f"id={r.get('id')} "
            f"created_at={r.get('created_at')} "
            f"symbol={r.get('symbol')} "
            f"strategy={sval(r.get('strategy'))} "
            f"timeframe={sval(r.get('timeframe'))} "
            f"reason={sval(r.get('reason'))} "
            f"payload_keys={payload_keys} "
            f"feature_keys={feature_keys} "
            f"payload={compact_json(payload)} "
            f"features={compact_json(features)}"
        )

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_SUMMARY")
    print("guard_table_exists=1")
    print(f"guard_rows_total={total_rows}")
    print(f"expected_strategy_block_rows={target_rows}")
    print(f"br_named_reason_rows={br_named_reason_rows}")
    print(f"sample_rows={len(samples)}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if target_rows > 0 and br_named_reason_rows > 0:
        print("VERDICT=EQUITY_GUARD_USES_BR_NAMED_REASON")
    elif target_rows > 0:
        print("VERDICT=EQUITY_GUARD_BLOCKS_EXPECTED_STRATEGY")
    elif total_rows > 0:
        print("VERDICT=EQUITY_GUARD_BLOCKS_OTHER_STRATEGIES")
    else:
        print("VERDICT=EQUITY_GUARD_NO_BLOCK_ROWS")

    print("EQUITY_PRE_SIGNAL_GUARD_REASON_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
