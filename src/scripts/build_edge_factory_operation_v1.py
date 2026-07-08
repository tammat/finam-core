from __future__ import annotations

import json
from decimal import Decimal
from datetime import datetime, UTC
from pathlib import Path

import psycopg2
import psycopg2.extras


OUT_JSON = Path("reports/edge_factory_operation_latest.json")
OUT_TXT = Path("reports/edge_factory_operation_latest.txt")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")



def scalar(cur, sql: str) -> int | float | str:
    cur.execute(sql)
    row = cur.fetchone()
    return list(row.values())[0] if row else 0


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            metrics = {
                "research_jobs": scalar(cur, "SELECT count(*) FROM analytics.parameter_search_job_v1"),
                "observations": scalar(cur, "SELECT count(*) FROM analytics.edge_observation_v1"),
                "candidates": scalar(cur, "SELECT count(*) FROM analytics.edge_candidate_v1"),
                "paper_active": scalar(cur, "SELECT count(*) FROM analytics.paper_runtime_candidate_v1 WHERE paper_status='ACTIVE'"),
                "paper_mtm_snapshots": scalar(cur, "SELECT count(*) FROM analytics.paper_portfolio_mtm_snapshot_v1"),
                "unsafe_rows": scalar(cur, "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed=true OR live_allowed=true"),
            }

            cur.execute("""
                SELECT
                    candidate_id,
                    strategy_code,
                    symbol,
                    timeframe,
                    trades,
                    round(net_after_tax, 6) AS net_after_tax,
                    round(max_drawdown, 6) AS max_drawdown,
                    market_model_version
                FROM analytics.paper_portfolio_mtm_snapshot_v1
                ORDER BY snapshot_id DESC
                LIMIT 20;
            """)
            paper_rows = [dict(r) for r in cur.fetchall()]

    payload = {
        "source_version": "EDGE_FACTORY_OPERATION_V1",
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": metrics,
        "paper_latest": paper_rows,
        "verdict": "EDGE_FACTORY_OPERATION_READY" if metrics["unsafe_rows"] == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    lines = [
        "=== EDGE_FACTORY_OPERATION_V1 ===",
        f"generated_at={payload['generated_at']}",
        f"research_jobs={metrics['research_jobs']}",
        f"observations={metrics['observations']}",
        f"candidates={metrics['candidates']}",
        f"paper_active={metrics['paper_active']}",
        f"paper_mtm_snapshots={metrics['paper_mtm_snapshots']}",
        f"unsafe_rows={metrics['unsafe_rows']}",
        f"VERDICT={payload['verdict']}",
    ]
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
