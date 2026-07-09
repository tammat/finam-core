from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

SOURCE_VERSION = "SIGNAL_FUNNEL_ANALYTICS_V1"


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

            stages: list[tuple[str, str, Decimal, dict[str, Any]]] = []

            stages.append(("SIGNALS", "Сигналы", *first_count(cur, [
                "public.signals",
                "public.virtual_signal_trades",
                "public.signal_lifecycle",
                "public.runtime_guard_signal_registry_v1",
                "public.gold_shadow_signals",
                "public.usdrub_shadow_signals",
                "public.lkoh_shadow_signals",
            ])))

            stages.append(("INTENTS", "Намерения исполнения", *first_count(cur, [
                "public.execution_intents",
                "public.portfolio_execution_queue",
                "public.oms_order_journal",
            ])))

            stages.append(("ORDERS", "Заявки", *first_count(cur, [
                "public.orders",
                "public.shadow_runtime_orders",
                "public.order_events",
                "public.order_projection",
            ])))

            stages.append(("ACKS", "Подтверждения заявок", *first_count(cur, [
                "public.order_acks",
                "public.broker_order_snapshots",
            ])))

            stages.append(("FILLS", "Исполнения", *first_count(cur, [
                "public.fills",
                "public.signal_fills",
                "public.shadow_runtime_fills",
            ])))

            stages.append(("TRADES", "Сделки", *first_count(cur, [
                "public.trades",
                "public.analytics_trades_normalized",
                "public.analytics_trades_continuous",
            ])))

            closed, ev = latest_paper_summary(cur, "trades_total")
            stages.append(("CLOSED_PAPER_TRADES", "Закрытые Paper-сделки", closed, ev))

            losses, ev = latest_paper_summary(cur, "losses_total")
            stages.append(("LOSSES", "Убыточные сделки", losses, ev))

            feedback, ev = first_count(cur, ["analytics.paper_execution_feedback_v1"])
            stages.append(("FEEDBACK_BLOCKERS", "Ограничения Feedback", feedback, ev))

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
