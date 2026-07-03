#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts

cat > sql/marketcore_ui/036_edge_discovery_use_market_universe_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_discovery_use_market_universe_v1 (
    id SMALLINT PRIMARY KEY,
    legacy_source TEXT NOT NULL DEFAULT 'marketcore_ui.paper_edge_research_candidates_v1',
    new_source TEXT NOT NULL DEFAULT 'marketcore_ui.market_universe_research_queue_v1',
    legacy_rows INTEGER NOT NULL DEFAULT 0,
    legacy_symbols INTEGER NOT NULL DEFAULT 0,
    queue_rows INTEGER NOT NULL DEFAULT 0,
    queue_symbols INTEGER NOT NULL DEFAULT 0,
    ranking_rows INTEGER NOT NULL DEFAULT 0,
    universe_rows INTEGER NOT NULL DEFAULT 0,
    migration_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    runtime_changed INTEGER NOT NULL DEFAULT 0,
    execution_changed INTEGER NOT NULL DEFAULT 0,
    orders_changed INTEGER NOT NULL DEFAULT 0,
    fills_changed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_discovery_use_market_universe_v1 TO alex;

COMMIT;

SELECT 'EDGE_DISCOVERY_USE_MARKET_UNIVERSE_SCHEMA_V1_READY' AS verdict;
SQL

cat > src/scripts/build_edge_discovery_use_market_universe_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1"


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    row = cur.fetchone()
    return int(list(row.values())[0] or 0)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1 ===")

            legacy_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.paper_edge_research_candidates_v1;")
            legacy_symbols = scalar(cur, "SELECT count(DISTINCT symbol) FROM marketcore_ui.paper_edge_research_candidates_v1;")
            queue_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
            queue_symbols = scalar(cur, "SELECT count(DISTINCT symbol) FROM marketcore_ui.market_universe_research_queue_v1;")
            ranking_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.market_universe_ranking_v1;")
            universe_rows = scalar(cur, "SELECT count(*) FROM marketcore_ui.paper_edge_market_universe_candidates_v1;")

            if queue_rows > 0 and queue_symbols > 1:
                status = "MARKET_UNIVERSE_ACTIVE"
                diagnosis = "Новый источник market_universe_research_queue_v1 готов и содержит мультиинструментальную очередь."
                action = "Использовать Research Queue как основной источник Edge/Validation; legacy BR-only оставить read-only."
            else:
                status = "BLOCKED_QUEUE_NOT_READY"
                diagnosis = "Новая Research Queue пуста или содержит один инструмент."
                action = "Проверить MARKET_UNIVERSE_RESEARCH_QUEUE_V1 и market bars."

            cur.execute("""
                INSERT INTO marketcore_ui.edge_discovery_use_market_universe_v1 (
                    id, legacy_rows, legacy_symbols, queue_rows, queue_symbols,
                    ranking_rows, universe_rows, migration_status, diagnosis,
                    recommended_action, runtime_changed, execution_changed,
                    orders_changed, fills_changed, micro_live_allowed,
                    refreshed_at, source_version, build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    0,0,0,0,0,now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    legacy_rows=EXCLUDED.legacy_rows,
                    legacy_symbols=EXCLUDED.legacy_symbols,
                    queue_rows=EXCLUDED.queue_rows,
                    queue_symbols=EXCLUDED.queue_symbols,
                    ranking_rows=EXCLUDED.ranking_rows,
                    universe_rows=EXCLUDED.universe_rows,
                    migration_status=EXCLUDED.migration_status,
                    diagnosis=EXCLUDED.diagnosis,
                    recommended_action=EXCLUDED.recommended_action,
                    runtime_changed=0,
                    execution_changed=0,
                    orders_changed=0,
                    fills_changed=0,
                    micro_live_allowed=0,
                    refreshed_at=now(),
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                legacy_rows, legacy_symbols, queue_rows, queue_symbols,
                ranking_rows, universe_rows, status, diagnosis, action,
                SOURCE_VERSION, build_id,
            ))

    print(f"legacy_rows={legacy_rows}")
    print(f"legacy_symbols={legacy_symbols}")
    print(f"queue_rows={queue_rows}")
    print(f"queue_symbols={queue_symbols}")
    print(f"ranking_rows={ranking_rows}")
    print(f"universe_rows={universe_rows}")
    print(f"migration_status={status}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

api = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = api.read_text()

if '/api/kg/v1/edge-discovery-use-market-universe' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    block = '''
            if path == "/api/kg/v1/edge-discovery-use-market-universe":
                row = fetch_one("""
                    SELECT
                        legacy_source,
                        new_source,
                        legacy_rows,
                        legacy_symbols,
                        queue_rows,
                        queue_symbols,
                        ranking_rows,
                        universe_rows,
                        migration_status,
                        diagnosis,
                        recommended_action,
                        runtime_changed,
                        execution_changed,
                        orders_changed,
                        fills_changed,
                        micro_live_allowed,
                        refreshed_at,
                        source_version
                    FROM marketcore_ui.edge_discovery_use_market_universe_v1
                    WHERE id=1;
                """)
                self.send_json(200, response("OK", row or {}, {
                    "source": "marketcore_ui.edge_discovery_use_market_universe_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_discovery_use_market_universe_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

api.write_text(s)
PY

cat > scripts/test_edge_discovery_use_market_universe_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/036_edge_discovery_use_market_universe_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_use_market_universe_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py >/tmp/use_market_universe_candidates_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/use_market_universe_ranking_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/use_market_universe_queue_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_use_market_universe_v1.py \
  | tee /tmp/edge_discovery_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_READY" \
  /tmp/edge_discovery_use_market_universe_v1.txt

status=$(psql -At -d finam_core -c "SELECT migration_status FROM marketcore_ui.edge_discovery_use_market_universe_v1 WHERE id=1;")
queue_symbols=$(psql -At -d finam_core -c "SELECT queue_symbols FROM marketcore_ui.edge_discovery_use_market_universe_v1 WHERE id=1;")
legacy_symbols=$(psql -At -d finam_core -c "SELECT legacy_symbols FROM marketcore_ui.edge_discovery_use_market_universe_v1 WHERE id=1;")

test "$status" = "MARKET_UNIVERSE_ACTIVE"
test "$queue_symbols" -gt 1

psql -d finam_core -c "
SELECT
    migration_status,
    legacy_rows,
    legacy_symbols,
    queue_rows,
    queue_symbols,
    ranking_rows,
    universe_rows,
    recommended_action
FROM marketcore_ui.edge_discovery_use_market_universe_v1
WHERE id=1;
"

psql -d finam_core -c "
SELECT queue_rank, symbol, timeframe, asset_class, total_score, research_priority
FROM marketcore_ui.market_universe_research_queue_v1
ORDER BY queue_rank
LIMIT 20;
"

echo "migration_status=$status"
echo "legacy_symbols=$legacy_symbols"
echo "queue_symbols=$queue_symbols"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_discovery_use_market_universe_v1.sh
scripts/test_edge_discovery_use_market_universe_v1.sh

echo "VERDICT=BUILD_EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1_OK"
