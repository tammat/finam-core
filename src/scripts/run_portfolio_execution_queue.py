from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import psycopg2

from finam_core.runtime.portfolio_execution_planner import PortfolioExecutionPlanner


def infer_group(symbol: str) -> str:
    s = symbol.upper()

    if any(x in s for x in ["LKOH", "GAZP", "NVTK", "TATN", "RNFT"]):
        return "OIL_GAS"

    if any(x in s for x in ["SBER", "VTBR", "T"]):
        return "BANKS"

    if any(x in s for x in ["MGNT", "LENT"]):
        return "RETAIL"

    if any(x in s for x in ["GMKN", "PLZL", "CHMF", "NLMK", "MAGN"]):
        return "METALS"

    return "OTHER"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    plan_id = datetime.now(timezone.utc).strftime("portfolio-plan-%Y%m%d-%H%M%S")

    conn = psycopg2.connect(dsn)
    planner = PortfolioExecutionPlanner()

    with conn:
        with conn.cursor() as cur:
            lookback_minutes = int(os.getenv("PORTFOLIO_QUEUE_LOOKBACK_MINUTES", "1440"))

            cur.execute("""
                select
                    symbol,
                    entry_price,
                    raw_json->'runtime_decision'->>'trade_quality_score' as quality_score,
                    raw_json->'runtime_decision'->>'trade_quality_grade' as quality_grade,
                    raw_json->'runtime_decision'->>'expected_value' as expected_value,
                    raw_json->'runtime_decision'->>'max_position_value' as allocated_capital,
                    raw_json->'runtime_decision'->>'recommended_qty' as allocated_qty
                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and decision = 'ALERT'
                  and created_at >= now() - (%s || ' minutes')::interval
                order by created_at desc
                limit 50
            """, (str(lookback_minutes),))

            candidates = []

            for row in cur.fetchall():
                (
                    symbol,
                    entry_price,
                    quality_score,
                    quality_grade,
                    expected_value,
                    allocated_capital,
                    allocated_qty,
                ) = row

                candidates.append({
                    "symbol": symbol,
                    "entry_price": float(entry_price or 0),
                    "quality_score": float(quality_score or 0),
                    "quality_grade": str(quality_grade or "D"),
                    "expected_value": float(expected_value or 0),
                    "allocated_capital": float(allocated_capital or 0),
                    "allocated_qty": int(float(allocated_qty or 0)),
                    "correlation_group": infer_group(str(symbol)),
                })

            plan = planner.build_plan(
                candidates=candidates,
                max_execute=int(os.getenv("PORTFOLIO_QUEUE_MAX_EXECUTE", "3")),
                min_quality_score=float(os.getenv("PORTFOLIO_QUEUE_MIN_QUALITY_SCORE", "45")),
            )

            inserted = 0
            updated = 0

            for item in plan:
                payload = {
                    "plan_id": plan_id,
                    "symbol": item.symbol,
                    "decision": item.decision,
                    "priority": item.priority,
                    "allocated_capital": item.allocated_capital,
                    "allocated_qty": item.allocated_qty,
                    "quality_score": item.quality_score,
                    "quality_grade": item.quality_grade,
                    "expected_value": item.expected_value,
                    "reason": item.reason,
                }

                queue_state = "READY" if item.decision == "EXECUTE" else "WATCH"

                cur.execute("""
                    insert into portfolio_execution_queue (
                        plan_id,
                        symbol,
                        priority,
                        queue_state,
                        decision,
                        allocated_capital,
                        allocated_qty,
                        quality_score,
                        quality_grade,
                        expected_value,
                        reason,
                        raw_json
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    on conflict(plan_id, symbol) do update set
                        updated_at = now(),
                        priority = excluded.priority,
                        queue_state = excluded.queue_state,
                        decision = excluded.decision,
                        allocated_capital = excluded.allocated_capital,
                        allocated_qty = excluded.allocated_qty,
                        quality_score = excluded.quality_score,
                        quality_grade = excluded.quality_grade,
                        expected_value = excluded.expected_value,
                        reason = excluded.reason,
                        raw_json = excluded.raw_json
                    returning (xmax = 0) as inserted
                """, (
                    plan_id,
                    item.symbol,
                    item.priority,
                    queue_state,
                    item.decision,
                    item.allocated_capital,
                    item.allocated_qty,
                    item.quality_score,
                    item.quality_grade,
                    item.expected_value,
                    item.reason,
                    json.dumps(payload, ensure_ascii=False, default=str),
                ))

                was_inserted = bool(cur.fetchone()[0])
                if was_inserted:
                    inserted += 1
                else:
                    updated += 1

    print(
        "PORTFOLIO_EXECUTION_QUEUE_OK "
        f"plan_id={plan_id} "
        f"candidates={len(candidates)} "
        f"queued={len(plan)} "
        f"inserted={inserted} "
        f"updated={updated}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
