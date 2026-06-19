#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# EQUITY_INTENT_ORIGIN_AUDIT_V1
# Read-only аудит происхождения execution_intents по equity.
# Фокус: SBER@MISX, старые intents без signals/source/strategy.


SYMBOL = os.getenv("EQUITY_FLOW_SYMBOL", "SBER@MISX")
LOOKBACK_DAYS = int(os.getenv("EQUITY_FLOW_LOOKBACK_DAYS", "60"))
SAMPLE_LIMIT = int(os.getenv("EQUITY_INTENT_SAMPLE_LIMIT", "50"))


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


def select_expr(cols: set[str], name: str, default: str = "NULL") -> str:
    if name in cols:
        return name
    return f"'{default}' as {name}"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    interval = f"{LOOKBACK_DAYS} days"

    print("=== EQUITY INTENT ORIGIN AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"symbol={SYMBOL}")
    print(f"lookback_days={LOOKBACK_DAYS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            has_intents = table_exists(cur, "execution_intents")
            has_signals = table_exists(cur, "signals")

        if not has_intents:
            print("EQUITY_INTENT_ORIGIN_AUDIT_SUMMARY")
            print("execution_intents_table=0")
            print("VERDICT=EQUITY_INTENT_TABLE_MISSING")
            print("EQUITY_INTENT_ORIGIN_AUDIT_V1_OK")
            return 0

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            intent_cols = columns(cur, "execution_intents")

            print("EQUITY_INTENT_SCHEMA_COLUMNS")
            print("EQUITY_INTENT_SCHEMA_COLUMN_ROW columns=" + ",".join(sorted(intent_cols)))
            print()

            created_expr = "created_at" if "created_at" in intent_cols else (
                "ts" if "ts" in intent_cols else (
                    "timestamp" if "timestamp" in intent_cols else "now()"
                )
            )

            payload_expr = "payload" if "payload" in intent_cols else "'{}'::jsonb as payload"
            strategy_expr = "strategy" if "strategy" in intent_cols else "'UNKNOWN' as strategy"
            status_expr = "status" if "status" in intent_cols else "'UNKNOWN' as status"
            source_expr = "source" if "source" in intent_cols else "'UNKNOWN' as source"
            signal_id_expr = "signal_id::text as signal_id" if "signal_id" in intent_cols else "'NO_SIGNAL_ID_COLUMN' as signal_id"
            side_expr = "side" if "side" in intent_cols else "'UNKNOWN' as side"
            qty_expr = "qty" if "qty" in intent_cols else "0 as qty"
            price_expr = "price" if "price" in intent_cols else "0 as price"

            cur.execute(
                f"""
                select
                    id,
                    {created_expr} as created_at,
                    symbol,
                    {strategy_expr},
                    {status_expr},
                    {source_expr},
                    {signal_id_expr},
                    {side_expr},
                    {qty_expr},
                    {price_expr},
                    {payload_expr}
                from execution_intents
                where symbol = %s
                  and {created_expr} >= now() - (%s::text)::interval
                order by {created_expr} asc, id asc
                limit %s
                """,
                (SYMBOL, interval, SAMPLE_LIMIT),
            )
            intent_samples = list(cur.fetchall())

            cur.execute(
                f"""
                select
                    coalesce({strategy_expr.split(' as ')[0]}, 'UNKNOWN') as strategy,
                    coalesce({status_expr.split(' as ')[0]}, 'UNKNOWN') as status,
                    coalesce({source_expr.split(' as ')[0]}, 'UNKNOWN') as source,
                    coalesce({signal_id_expr.split(' as ')[0]}, 'NULL') as signal_id,
                    count(*) as intents,
                    min({created_expr}) as first_ts,
                    max({created_expr}) as last_ts
                from execution_intents
                where symbol = %s
                  and {created_expr} >= now() - (%s::text)::interval
                group by 1,2,3,4
                order by intents desc, last_ts desc
                """,
                (SYMBOL, interval),
            )
            intent_groups = list(cur.fetchall())

            signal_total = 0
            if has_signals:
                signal_cols = columns(cur, "signals")
                signal_ts = "created_at" if "created_at" in signal_cols else (
                    "ts" if "ts" in signal_cols else (
                        "timestamp" if "timestamp" in signal_cols else None
                    )
                )
                if signal_ts and "symbol" in signal_cols:
                    cur.execute(
                        f"""
                        select count(*) as signals
                        from signals
                        where symbol = %s
                          and {signal_ts} >= now() - (%s::text)::interval
                        """,
                        (SYMBOL, interval),
                    )
                    signal_total = int(cur.fetchone()["signals"])

    print("EQUITY_INTENT_ORIGIN_GROUP_ROWS")
    total_intents = 0
    orphan_intents = 0

    for r in intent_groups:
        intents = int(r["intents"])
        total_intents += intents

        signal_id = sval(r.get("signal_id"), "NULL")
        source = sval(r.get("source"))
        strategy = sval(r.get("strategy"))
        status = sval(r.get("status"))

        is_orphan = (
            signal_id in {"NO_SIGNAL_ID_COLUMN", "NULL", "UNKNOWN", ""}
            and source in {"UNKNOWN", "NULL", ""}
            and strategy in {"UNKNOWN", "NULL", ""}
        )

        if is_orphan:
            orphan_intents += intents

        print(
            "EQUITY_INTENT_ORIGIN_GROUP_ROW "
            f"strategy={strategy} "
            f"status={status} "
            f"source={source} "
            f"signal_id={signal_id} "
            f"intents={intents} "
            f"first_ts={r['first_ts']} "
            f"last_ts={r['last_ts']} "
            f"classification={'ORPHAN_LEGACY_INTENTS' if is_orphan else 'REVIEW_REQUIRED'}"
        )

    print()
    print("EQUITY_INTENT_ORIGIN_SAMPLE_ROWS")
    for r in intent_samples:
        payload = r.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        print(
            "EQUITY_INTENT_ORIGIN_SAMPLE_ROW "
            f"id={r.get('id')} "
            f"created_at={r.get('created_at')} "
            f"symbol={r.get('symbol')} "
            f"strategy={sval(r.get('strategy'))} "
            f"status={sval(r.get('status'))} "
            f"source={sval(r.get('source'))} "
            f"signal_id={sval(r.get('signal_id'))} "
            f"side={sval(r.get('side'))} "
            f"qty={r.get('qty')} "
            f"price={r.get('price')} "
            f"payload_keys={','.join(sorted(payload.keys())) if payload else 'NO_PAYLOAD'} "
            f"payload={compact_json(payload)}"
        )

    print()
    print("EQUITY_INTENT_ORIGIN_AUDIT_SUMMARY")
    print("execution_intents_table=1")
    print(f"signals_total={signal_total}")
    print(f"execution_intents_total={total_intents}")
    print(f"orphan_legacy_intents={orphan_intents}")
    print(f"review_required_intents={total_intents - orphan_intents}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if total_intents > 0 and orphan_intents == total_intents and signal_total == 0:
        print("VERDICT=EQUITY_INTENTS_ARE_ORPHAN_LEGACY")
    elif total_intents > 0 and signal_total == 0:
        print("VERDICT=EQUITY_INTENTS_WITHOUT_SIGNALS_REVIEW_REQUIRED")
    elif total_intents == 0 and signal_total == 0:
        print("VERDICT=EQUITY_NO_INTENTS_NO_SIGNALS")
    else:
        print("VERDICT=EQUITY_INTENT_ORIGIN_REVIEW_REQUIRED")

    print("EQUITY_INTENT_ORIGIN_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
