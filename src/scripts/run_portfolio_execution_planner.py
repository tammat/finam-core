from __future__ import annotations

import os

import psycopg2

from finam_core.runtime.portfolio_execution_planner import (
    PortfolioExecutionPlanner,
)


def infer_group(symbol: str) -> str:
    s = symbol.upper()

    if any(x in s for x in ["LKOH", "GAZP", "NVTK", "TATN", "RNFT"]):
        return "OIL_GAS"

    if any(x in s for x in ["SBER", "VTBR", "T"]):
        return "BANKS"

    if any(x in s for x in ["MGNT", "LENT"]):
        return "RETAIL"

    return "OTHER"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    planner = PortfolioExecutionPlanner()

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    symbol,

                    entry_price,

                    raw_json->'runtime_decision'->>'trade_quality_score' as quality_score,
                    raw_json->'runtime_decision'->>'trade_quality_grade' as quality_grade,

                    raw_json->'runtime_decision'->>'expected_value' as expected_value,

                    raw_json->'runtime_decision'->>'allocated_capital' as allocated_capital,
                    raw_json->'runtime_decision'->>'allocated_qty' as allocated_qty

                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and decision = 'ALERT'
                order by created_at desc
                limit 50
            """)

            rows = cur.fetchall()

            candidates: list[dict] = []

            for row in rows:
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
                    "entry_price": float(entry_price or 0.0),

                    "quality_score": float(quality_score or 0.0),
                    "quality_grade": str(quality_grade or "D"),

                    "expected_value": float(expected_value or 0.0),

                    "allocated_capital": float(allocated_capital or 0.0),
                    "allocated_qty": int(float(allocated_qty or 0)),

                    "correlation_group": infer_group(str(symbol)),
                })

            plan = planner.build_plan(
                candidates=candidates,
                max_execute=3,
            )

            print("\n=== PORTFOLIO EXECUTION PLAN ===\n", flush=True)

            for item in plan:

                print(
                    f"{item.priority:02d}. "
                    f"{item.symbol:<12} "
                    f"{item.decision:<8} "
                    f"grade={item.quality_grade:<2} "
                    f"score={item.quality_score:<6.2f} "
                    f"capital={item.allocated_capital:<10.2f} "
                    f"qty={item.allocated_qty:<5d} "
                    f"ev={item.expected_value:<8.2f} "
                    f"reason={item.reason}",
                    flush=True,
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
