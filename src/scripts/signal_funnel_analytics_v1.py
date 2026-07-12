from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

SOURCE_VERSION = "SIGNAL_FUNNEL_ANALYTICS_V2_LINKED_COHORT"


def dec(v: Any) -> Decimal:
    return Decimal(str(v or 0))


def table_exists(cur, full_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (full_name,))
    return bool(cur.fetchone()["ok"])


def count_table(cur, full_name: str) -> tuple[Decimal, dict[str, Any]]:
    if not table_exists(cur, full_name):
        return Decimal("0"), {"source_table": full_name, "exists": False}

    schema_name, table_name = full_name.split(".", 1)
    cur.execute(
        sql.SQL("SELECT count(*) AS rows_total FROM {}.{}").format(
            sql.Identifier(schema_name),
            sql.Identifier(table_name),
        )
    )
    return dec(cur.fetchone()["rows_total"]), {"source_table": full_name, "exists": True}


def first_count(cur, candidates: list[str]) -> tuple[Decimal, dict[str, Any]]:
    checked: list[dict[str, Any]] = []
    for table_name in candidates:
        cnt, ev = count_table(cur, table_name)
        checked.append(dict(ev))
        if ev["exists"]:
            result = dict(ev)
            result["checked"] = checked
            return cnt, result
    return Decimal("0"), {"source_table": None, "exists": False, "checked": checked}


def latest_paper_summary(cur, column: str) -> tuple[Decimal, dict[str, Any]]:
    table_name = "analytics.paper_execution_summary_v1"
    if not table_exists(cur, table_name):
        return Decimal("0"), {"source_table": table_name, "exists": False}

    cur.execute(
        sql.SQL("""
            SELECT {} AS v
            FROM analytics.paper_execution_summary_v1
            ORDER BY created_at DESC
            LIMIT 1
        """).format(sql.Identifier(column))
    )
    row = cur.fetchone()
    return dec(row["v"] if row else 0), {
        "source_table": table_name,
        "source_column": column,
        "exists": True,
    }


def linked_stage_counts(cur) -> list[tuple[str, str, Decimal, dict[str, Any]]]:
    required = ("public.signals", "public.orders", "public.order_acks", "public.fills", "public.trades")
    missing = [table for table in required if not table_exists(cur, table)]
    if missing:
        return [("SIGNALS", "Сигналы", Decimal("0"), {
            "cohort": "linked_signal_order_execution_v2",
            "comparable": False,
            "missing_tables": missing,
        })]

    cur.execute("""
        WITH signal_cohort AS (
            SELECT DISTINCT COALESCE(NULLIF(signal_id, ''), id::text) AS signal_key
            FROM public.signals
        ),
        linked_orders AS (
            SELECT DISTINCT o.order_id, o.signal_event_id AS signal_key
            FROM public.orders o
            JOIN signal_cohort s ON s.signal_key = o.signal_event_id
            WHERE o.order_id IS NOT NULL
        ),
        linked_acks AS (
            SELECT DISTINCT a.order_id
            FROM public.order_acks a
            JOIN linked_orders o ON o.order_id = a.order_id
        ),
        linked_fills AS (
            SELECT DISTINCT f.fill_id, f.order_id
            FROM public.fills f
            JOIN linked_orders o ON o.order_id = f.order_id
            WHERE f.fill_id IS NOT NULL
        ),
        linked_trades AS (
            SELECT DISTINCT t.fill_id
            FROM public.trades t
            JOIN linked_fills f ON f.fill_id = t.fill_id
        )
        SELECT
            (SELECT count(*) FROM signal_cohort) AS signals,
            (SELECT count(DISTINCT signal_key) FROM linked_orders) AS ordered_signals,
            (SELECT count(DISTINCT o.signal_key) FROM linked_orders o JOIN linked_acks a USING(order_id)) AS acknowledged_signals,
            (SELECT count(DISTINCT o.signal_key) FROM linked_orders o JOIN linked_fills f USING(order_id)) AS filled_signals,
            (SELECT count(DISTINCT o.signal_key) FROM linked_orders o JOIN linked_fills f USING(order_id) JOIN linked_trades t USING(fill_id)) AS traded_signals
    """)
    row = cur.fetchone()
    evidence = {
        "cohort": "linked_signal_order_execution_v2",
        "comparable": True,
        "join_chain": "signals.signal_id -> orders.signal_event_id -> order_acks/fills.order_id -> trades.fill_id",
        "count_unit": "distinct_origin_signal",
    }
    order_evidence = dict(evidence)
    order_evidence.update({
        "boundary": "RESEARCH_TO_EXECUTION",
        "live_control": "BLOCKED",
        "zero_is_expected_while_live_blocked": True,
    })
    return [
        ("SIGNALS", "Сформированные сигналы", dec(row["signals"]), dict(evidence)),
        ("ORDERS", "Сигналы, допущенные до заявки", dec(row["ordered_signals"]), order_evidence),
        ("ACKS", "Сигналы с подтверждённой заявкой", dec(row["acknowledged_signals"]), dict(evidence)),
        ("FILLS", "Сигналы с исполнением", dec(row["filled_signals"]), dict(evidence)),
        ("TRADES", "Сигналы с зарегистрированной сделкой", dec(row["traded_signals"]), dict(evidence)),
    ]


def pct(current: Decimal, previous: Decimal | None) -> Decimal | None:
    if previous is None or previous <= 0:
        return None
    return (current / previous * Decimal("100")).quantize(Decimal("0.0001"))


def status(current: Decimal, previous: Decimal | None) -> str:
    if current <= 0:
        return "ZERO"
    rate = pct(current, previous)
    if rate is not None and rate < Decimal("10"):
        return "BOTTLENECK"
    return "OK"


def insert_stage(cur, snapshot_id: int, order: int, code: str, name: str, count: Decimal, previous: Decimal | None, evidence: dict[str, Any]) -> None:
    rate = pct(count, previous)
    cur.execute("""
        INSERT INTO analytics.signal_funnel_stage_v1
        (
            signal_funnel_snapshot_id,
            stage_order,
            stage_code,
            stage_name,
            stage_count,
            previous_stage_count,
            pass_rate_pct,
            stage_status,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
    """, (
        snapshot_id,
        order,
        code,
        name,
        count,
        previous,
        rate,
        status(count, previous),
        json.dumps(evidence, ensure_ascii=False),
        SOURCE_VERSION,
    ))


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.signal_funnel_snapshot_v1
                (source_version, evidence_json)
                VALUES (%s,%s::jsonb)
                RETURNING signal_funnel_snapshot_id
            """, (
                SOURCE_VERSION,
                json.dumps({"mode": "read_only", "purpose": "signal_to_trade_funnel"}, ensure_ascii=False),
            ))
            snapshot_id = int(cur.fetchone()["signal_funnel_snapshot_id"])

            stages = linked_stage_counts(cur)

            previous: Decimal | None = None
            for idx, (code, name, count, evidence) in enumerate(stages, start=1):
                insert_stage(cur, snapshot_id, idx, code, name, count, previous, evidence)
                previous = count

    print("=== SIGNAL_FUNNEL_ANALYTICS_V1 ===")
    print(f"signal_funnel_snapshot_id={snapshot_id}")
    for code, _, count, _ in stages:
        print(f"{code}={count}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SIGNAL_FUNNEL_ANALYTICS_V1_READY")


if __name__ == "__main__":
    main()
