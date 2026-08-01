from __future__ import annotations

import argparse
import os

import psycopg


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics.orphan_lifecycle_quarantine_v1 (
                lifecycle_id BIGINT PRIMARY KEY, symbol TEXT NOT NULL,
                previous_remaining_qty NUMERIC NOT NULL, lifecycle_snapshot JSONB NOT NULL,
                quarantined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                reason_code TEXT NOT NULL, restored_at TIMESTAMPTZ
            )
            """
        )
        cur.execute(
            """
            SELECT l.id,l.symbol,l.remaining_qty
            FROM position_lifecycle_state l
            LEFT JOIN real_portfolio_positions p ON p.symbol=l.symbol AND p.qty<>0
            WHERE l.remaining_qty<>0 AND l.updated_at<now()-interval '24 hours'
              AND p.symbol IS NULL
              AND COALESCE(l.raw->>'source','') IN (
                  'paper_pipeline_lifecycle_on_fill_v1','trailing_order_manager')
            ORDER BY l.id FOR UPDATE OF l
            """
        )
        rows = cur.fetchall()
        print(f"ORPHAN_LIFECYCLE_CANDIDATES count={len(rows)}")
        for lifecycle_id, symbol, qty in rows:
            print(f"candidate id={lifecycle_id} symbol={symbol} qty={qty}")

        if args.apply and rows:
            cur.execute(
                """
                INSERT INTO analytics.orphan_lifecycle_quarantine_v1 (
                    lifecycle_id,symbol,previous_remaining_qty,lifecycle_snapshot,reason_code
                )
                SELECT l.id,l.symbol,l.remaining_qty,to_jsonb(l.*),
                       'NO_CURRENT_PORTFOLIO_POSITION_PREMARKET'
                FROM position_lifecycle_state l
                WHERE l.id=ANY(%s)
                ON CONFLICT (lifecycle_id) DO NOTHING
                """,
                ([row[0] for row in rows],),
            )
            cur.execute(
                """
                UPDATE position_lifecycle_state
                SET remaining_qty=0, trailing_active=false,
                    raw=COALESCE(raw,'{}'::jsonb) || jsonb_build_object(
                        'quarantined',true,
                        'quarantine_reason','NO_CURRENT_PORTFOLIO_POSITION_PREMARKET'),
                    updated_at=now()
                WHERE id=ANY(%s)
                """,
                ([row[0] for row in rows],),
            )
            print(f"ORPHAN_LIFECYCLE_QUARANTINED count={cur.rowcount}")
        conn.commit()

    print("VERDICT=ORPHAN_LIFECYCLE_QUARANTINE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
