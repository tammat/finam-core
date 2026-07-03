#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_PIPELINE_V2_BUILDER_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_edge_pipeline_snapshot_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_PIPELINE_V2_BUILDER_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_PIPELINE_V2_BUILDER_V1 ===")

            cur.execute("DELETE FROM analytics.edge_pipeline_snapshot_v1;")

            cur.execute("""
                INSERT INTO analytics.edge_pipeline_snapshot_v1 (
                    symbol,
                    display_name,
                    asset_class,
                    timeframe,
                    strategy_family,

                    pipeline_stage,
                    overall_status,

                    ranking_score,
                    research_priority,
                    research_status,

                    validation_status,
                    validation_score,

                    robustness_status,
                    robustness_score,

                    oos_status,
                    oos_score,

                    backtest_status,
                    backtest_score,

                    paper_status,
                    paper_progress,
                    paper_trades,

                    risk_status,
                    trading_status,
                    runtime_status,

                    source_version,
                    build_id,
                    refreshed_at
                )
                SELECT
                    q.symbol,
                    COALESCE(NULLIF(i.display_name, ''), q.symbol) AS display_name,
                    COALESCE(NULLIF(i.asset_class, ''), q.asset_class) AS asset_class,
                    q.timeframe,
                    COALESCE(NULLIF(q.recommended_strategy_family, ''), 'UNASSIGNED') AS strategy_family,

                    20::smallint AS pipeline_stage,
                    'RESEARCH'::text AS overall_status,

                    COALESCE(q.total_score, r.total_score, 0)::numeric(20,6) AS ranking_score,
                    COALESCE(NULLIF(q.research_priority, ''), 'NORMAL') AS research_priority,
                    COALESCE(NULLIF(q.research_status, ''), 'QUEUED') AS research_status,

                    'NOT_STARTED'::text AS validation_status,
                    0::numeric(20,6) AS validation_score,

                    'NOT_STARTED'::text AS robustness_status,
                    0::numeric(20,6) AS robustness_score,

                    'NOT_STARTED'::text AS oos_status,
                    0::numeric(20,6) AS oos_score,

                    'NOT_STARTED'::text AS backtest_status,
                    0::numeric(20,6) AS backtest_score,

                    'NOT_STARTED'::text AS paper_status,
                    0::numeric(10,2) AS paper_progress,
                    0::integer AS paper_trades,

                    'NOT_READY'::text AS risk_status,
                    'NOT_READY'::text AS trading_status,
                    'UNKNOWN'::text AS runtime_status,

                    %s AS source_version,
                    %s AS build_id,
                    now() AS refreshed_at
                FROM marketcore_ui.market_universe_research_queue_v1 q
                LEFT JOIN marketcore_ui.market_universe_ranking_v1 r
                  ON r.symbol = q.symbol
                 AND r.timeframe = q.timeframe
                LEFT JOIN marketcore.instrument_reference_v1 i
                  ON i.symbol = q.symbol
                LEFT JOIN LATERAL (
                    SELECT ms.bar_ts
                    FROM marketcore.market_snapshot_v1 ms
                    WHERE ms.symbol = q.symbol
                      AND ms.timeframe = q.timeframe
                    ORDER BY ms.bar_ts DESC
                    LIMIT 1
                ) ms ON true
                ORDER BY q.queue_rank
                ON CONFLICT (symbol, timeframe, strategy_family) DO UPDATE SET
                    display_name=EXCLUDED.display_name,
                    asset_class=EXCLUDED.asset_class,
                    pipeline_stage=EXCLUDED.pipeline_stage,
                    overall_status=EXCLUDED.overall_status,
                    ranking_score=EXCLUDED.ranking_score,
                    research_priority=EXCLUDED.research_priority,
                    research_status=EXCLUDED.research_status,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (SOURCE_VERSION, build_id))

            cur.execute("SELECT count(*) AS rows FROM analytics.edge_pipeline_snapshot_v1;")
            rows = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT count(*) AS duplicates
                FROM (
                    SELECT symbol, timeframe, strategy_family, count(*) AS cnt
                    FROM analytics.edge_pipeline_snapshot_v1
                    GROUP BY symbol, timeframe, strategy_family
                    HAVING count(*) > 1
                ) d;
            """)
            duplicates = int(cur.fetchone()["duplicates"])

            cur.execute("SELECT count(DISTINCT symbol) AS symbols FROM analytics.edge_pipeline_snapshot_v1;")
            symbols = int(cur.fetchone()["symbols"])

    print(f"rows_written={rows}")
    print(f"symbols={symbols}")
    print(f"duplicates={duplicates}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_PIPELINE_V2_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_pipeline_v2_builder_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PIPELINE_V2_BUILDER_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_pipeline_snapshot_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_snapshot_v1.py \
  | tee /tmp/edge_pipeline_v2_builder_v1.txt

grep -q "VERDICT=EDGE_PIPELINE_V2_BUILDER_V1_READY" \
  /tmp/edge_pipeline_v2_builder_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_pipeline_snapshot_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM analytics.edge_pipeline_snapshot_v1;")
duplicates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
    SELECT symbol, timeframe, strategy_family, count(*) AS cnt
    FROM analytics.edge_pipeline_snapshot_v1
    GROUP BY symbol, timeframe, strategy_family
    HAVING count(*) > 1
) d;
")
bad_names=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_pipeline_snapshot_v1
WHERE display_name = '' OR display_name IS NULL;
")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$duplicates" = "0"
test "$bad_names" = "0"

psql -d finam_core -c "
SELECT
    symbol,
    display_name,
    asset_class,
    timeframe,
    strategy_family,
    pipeline_stage,
    overall_status,
    ranking_score,
    research_priority,
    research_status,
    validation_status,
    risk_status,
    trading_status
FROM analytics.edge_pipeline_snapshot_v1
ORDER BY ranking_score DESC, symbol, timeframe
LIMIT 30;
"

echo "edge_pipeline_rows=$rows"
echo "edge_pipeline_symbols=$symbols"
echo "duplicates=$duplicates"
echo "bad_names=$bad_names"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_PIPELINE_V2_BUILDER_V1_READY"
echo "VERDICT=TEST_EDGE_PIPELINE_V2_BUILDER_V1_OK"
SH_TEST

chmod +x scripts/test_edge_pipeline_v2_builder_v1.sh
scripts/test_edge_pipeline_v2_builder_v1.sh

echo "VERDICT=BUILD_EDGE_PIPELINE_V2_BUILDER_V1_OK"
