#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts

cat > sql/marketcore_ui/037_edge_validation_use_market_universe_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_validation_use_market_universe_v1 (
    validation_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    source_queue_rank INTEGER,
    total_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    research_priority TEXT NOT NULL DEFAULT '',
    ranking_status TEXT NOT NULL DEFAULT '',

    validation_source TEXT NOT NULL DEFAULT 'marketcore_ui.market_universe_research_queue_v1',
    legacy_source TEXT NOT NULL DEFAULT 'marketcore_ui.paper_edge_research_candidates_v1',

    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    validation_stage TEXT NOT NULL DEFAULT 'QUEUE',
    recommended_action TEXT NOT NULL DEFAULT '',

    runtime_changed INTEGER NOT NULL DEFAULT 0,
    execution_changed INTEGER NOT NULL DEFAULT 0,
    orders_changed INTEGER NOT NULL DEFAULT 0,
    fills_changed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_validation_use_market_universe_v1 TO alex;

COMMIT;

SELECT 'EDGE_VALIDATION_USE_MARKET_UNIVERSE_SCHEMA_V1_READY' AS verdict;
SQL

cat > src/scripts/build_edge_validation_use_market_universe_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1 ===")

            cur.execute("DELETE FROM marketcore_ui.edge_validation_use_market_universe_v1;")

            cur.execute("""
                SELECT
                    queue_rank,
                    symbol,
                    timeframe,
                    asset_class,
                    total_score,
                    research_priority,
                    ranking_status,
                    recommended_strategy_family
                FROM marketcore_ui.market_universe_research_queue_v1
                ORDER BY queue_rank
                LIMIT 50;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            for rank, r in enumerate(rows, start=1):
                priority = str(r.get("research_priority") or "")
                score = r.get("total_score") or 0
                strategy = r.get("recommended_strategy_family") or "MARKET_UNIVERSE_EDGE"

                if priority == "HIGH":
                    status = "READY_FOR_VALIDATION"
                    action = "Передать в проверку edge по новой Market Universe queue."
                elif priority == "MEDIUM":
                    status = "WATCH_VALIDATION"
                    action = "Оставить в очереди проверки после HIGH-кандидатов."
                else:
                    status = "WAIT_PRIORITY"
                    action = "Ждать повышения рейтинга или свежих данных."

                cur.execute("""
                    INSERT INTO marketcore_ui.edge_validation_use_market_universe_v1 (
                        validation_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        strategy,
                        side,
                        source_queue_rank,
                        total_score,
                        research_priority,
                        ranking_status,
                        validation_status,
                        validation_stage,
                        recommended_action,
                        runtime_changed,
                        execution_changed,
                        orders_changed,
                        fills_changed,
                        micro_live_allowed,
                        refreshed_at,
                        source_version,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,'ANY',%s,%s,%s,%s,%s,'QUEUE',%s,
                        0,0,0,0,0,now(),%s,%s
                    );
                """, (
                    rank,
                    r.get("symbol") or "",
                    r.get("timeframe") or "",
                    r.get("asset_class") or "",
                    strategy,
                    r.get("queue_rank"),
                    score,
                    priority,
                    r.get("ranking_status") or "",
                    status,
                    action,
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_validation_use_market_universe_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT validation_status, count(*) AS rows
                FROM marketcore_ui.edge_validation_use_market_universe_v1
                GROUP BY validation_status
                ORDER BY validation_status;
            """)
            groups = cur.fetchall()

            cur.execute("""
                SELECT count(DISTINCT symbol) AS symbols
                FROM marketcore_ui.edge_validation_use_market_universe_v1;
            """)
            symbols = int(cur.fetchone()["symbols"] or 0)

    print(f"rows_written={rows_written}")
    print(f"symbols={symbols}")
    for g in groups:
        print(f"validation_status_{g['validation_status']}={g['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_validation_use_market_universe_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/037_edge_validation_use_market_universe_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_validation_use_market_universe_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py >/tmp/validation_use_market_universe_candidates_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/validation_use_market_universe_ranking_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/validation_use_market_universe_queue_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_use_market_universe_v1.py \
  | tee /tmp/edge_validation_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_READY" \
  /tmp/edge_validation_use_market_universe_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_use_market_universe_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.edge_validation_use_market_universe_v1;")
ready=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.edge_validation_use_market_universe_v1 WHERE validation_status='READY_FOR_VALIDATION';")
br_only=$(psql -At -d finam_core -c "SELECT count(*) = count(*) FILTER (WHERE symbol LIKE 'BR%') FROM marketcore_ui.edge_validation_use_market_universe_v1;")

test "$rows" -gt 0
test "$symbols" -gt 1
test "$ready" -gt 0
test "$br_only" = "f"

psql -d finam_core -c "
SELECT
    validation_rank,
    symbol,
    timeframe,
    asset_class,
    strategy,
    total_score,
    research_priority,
    validation_status
FROM marketcore_ui.edge_validation_use_market_universe_v1
ORDER BY validation_rank
LIMIT 30;
"

echo "validation_rows=$rows"
echo "validation_symbols=$symbols"
echo "ready_for_validation=$ready"
echo "br_only=$br_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_validation_use_market_universe_v1.sh
scripts/test_edge_validation_use_market_universe_v1.sh

echo "VERDICT=BUILD_EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1_OK"
