from __future__ import annotations
import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SQL = """
WITH base AS (
    SELECT
        id,
        trade_id,
        db_trade_id,
        symbol,
        strategy,
        trade_source,
        ts,
        snapshot #>> '{attribution,signal_id}' AS signal_id,
        snapshot #>> '{attribution,fill_id}' AS fill_id,
        snapshot #>> '{attribution,trade_id}' AS payload_trade_id
    FROM trade_context_snapshots
    WHERE trade_source='paper'
)
SELECT
    count(*) AS snapshots,
    count(b.signal_id) AS snapshots_with_signal_id,
    count(b.fill_id) AS snapshots_with_fill_id,
    count(b.payload_trade_id) AS snapshots_with_payload_trade_id,
    count(f.fill_id) AS linked_fills,
    count(sf.fill_id) AS linked_signal_fills,
    count(s.signal_id) AS linked_signals,
    count(sqa.signal_id) AS linked_signal_quality
FROM base b
LEFT JOIN fills f ON f.fill_id = b.fill_id
LEFT JOIN signal_fills sf ON sf.fill_id = b.fill_id
LEFT JOIN signals s ON s.signal_id = b.signal_id
LEFT JOIN signal_quality_audit_v1 sqa ON sqa.signal_id = b.signal_id;
"""

def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== PAPER_RUNTIME_KG_RELATION_COVERAGE_V1 ===")
            cur.execute(SQL)
            row = cur.fetchone()
            cols = [d[0] for d in cur.description]
            for k, v in zip(cols, row):
                print(f"{k}={v}")
            print("VERDICT=PAPER_RUNTIME_KG_RELATION_COVERAGE_V1_READY")

if __name__ == "__main__":
    main()
