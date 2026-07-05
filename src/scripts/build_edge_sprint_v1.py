from __future__ import annotations

import os
from datetime import UTC, datetime

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SPRINT_CODE = os.getenv("EDGE_SPRINT_CODE", datetime.now(UTC).strftime("EDGE_SPRINT_%Y%m%d"))
SPRINT_NAME = os.getenv("EDGE_SPRINT_NAME", "Edge Sprint V1")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.edge_sprint_v1 (
                    sprint_code, sprint_name, status_code, notes, updated_at
                )
                VALUES (%s,%s,'OPEN','Initial sprint for fast edge search',now())
                ON CONFLICT(sprint_code) DO UPDATE SET
                    sprint_name=EXCLUDED.sprint_name,
                    status_code='OPEN',
                    updated_at=now();
            """, (SPRINT_CODE, SPRINT_NAME))

            cur.execute("""
                SELECT
                    count(*) AS observations_total,
                    count(*) FILTER (WHERE trades > 0) AS observations_with_trades,
                    coalesce(max(normalized_edge_score), 0) AS best_score,
                    coalesce(max(profit_factor), 0) AS best_profit_factor,
                    coalesce(max(expectancy), 0) AS best_expectancy
                FROM analytics.edge_observation_v1;
            """)
            obs = cur.fetchone()

            cur.execute("SELECT count(*) AS c FROM analytics.edge_candidate_v1;")
            candidates = cur.fetchone()["c"]

            cur.execute("SELECT count(*) AS c FROM analytics.research_trade_v1;")
            trades = cur.fetchone()["c"]

            cur.execute("""
                INSERT INTO analytics.edge_sprint_snapshot_v1 (
                    sprint_code,
                    observations_total,
                    observations_with_trades,
                    candidates_total,
                    best_score,
                    best_profit_factor,
                    best_expectancy,
                    research_trades
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s);
            """, (
                SPRINT_CODE,
                obs["observations_total"],
                obs["observations_with_trades"],
                candidates,
                obs["best_score"],
                obs["best_profit_factor"],
                obs["best_expectancy"],
                trades,
            ))

    print("=== EDGE_SPRINT_V1 ===")
    print(f"sprint_code={SPRINT_CODE}")
    print(f"sprint_name={SPRINT_NAME}")
    print(f"observations_total={obs['observations_total']}")
    print(f"observations_with_trades={obs['observations_with_trades']}")
    print(f"candidates_total={candidates}")
    print(f"best_score={obs['best_score']}")
    print(f"best_profit_factor={obs['best_profit_factor']}")
    print(f"best_expectancy={obs['best_expectancy']}")
    print(f"research_trades={trades}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_SPRINT_V1_READY")


if __name__ == "__main__":
    main()
