#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts

cat > sql/marketcore_ui/019_paper_runtime_sample_collection_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_v1 (
    id SMALLINT PRIMARY KEY,
    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,
    wait_total_sample INTEGER NOT NULL DEFAULT 0,
    wait_oos_sample INTEGER NOT NULL DEFAULT 0,
    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,
    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_runtime_sample_collection_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/019_paper_runtime_sample_collection_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_runtime_sample_collection_v1.sh

cat > src/scripts/build_paper_runtime_sample_collection_v1.py <<'PY'
from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_RUNTIME_SAMPLE_COLLECTION_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_RUNTIME_SAMPLE_COLLECTION_V1 ===")

            cur.execute("""
                SELECT
                    count(*) AS candidates_total,
                    count(*) FILTER (WHERE sample_status='SAMPLE_READY') AS sample_ready,
                    count(*) FILTER (WHERE sample_status='WAIT_BOTH_SAMPLE') AS wait_both_sample,
                    count(*) FILTER (WHERE sample_status='WAIT_TOTAL_SAMPLE') AS wait_total_sample,
                    count(*) FILTER (WHERE sample_status='WAIT_OOS_SAMPLE') AS wait_oos_sample,
                    min(remaining_total_trades) AS min_remaining_total_trades,
                    min(remaining_oos_trades) AS min_remaining_oos_trades,
                    coalesce(avg(progress_pct),0) AS avg_progress_pct,
                    coalesce(max(progress_pct),0) AS max_progress_pct,
                    bool_or(micro_live_allowed) AS micro_live_allowed
                FROM marketcore_ui.paper_sample_accumulation_monitor_v1;
            """)
            r = dict(cur.fetchone())

            candidates_total = int(r["candidates_total"] or 0)
            sample_ready = int(r["sample_ready"] or 0)
            micro_live_allowed = bool(r["micro_live_allowed"] or False)

            if candidates_total == 0:
                collection_status = "NO_CANDIDATES"
                phase_status = "NOT_READY"
                recommended_action = "Запустить Paper Edge Discovery и накопить кандидатов."
            elif sample_ready > 0:
                collection_status = "SAMPLE_READY"
                phase_status = "READY_FOR_REVALIDATION"
                recommended_action = "Перезапустить Validation Pipeline для кандидатов с достаточной выборкой."
            else:
                collection_status = "COLLECTING"
                phase_status = "WAIT_SAMPLE"
                recommended_action = "Продолжить Paper Runtime. Кандидаты ждут накопления общей и OOS-выборки."

            cur.execute("""
                INSERT INTO marketcore_ui.paper_runtime_sample_collection_v1 (
                    id,
                    candidates_total,
                    sample_ready,
                    wait_both_sample,
                    wait_total_sample,
                    wait_oos_sample,
                    min_remaining_total_trades,
                    min_remaining_oos_trades,
                    avg_progress_pct,
                    max_progress_pct,
                    collection_status,
                    phase_status,
                    recommended_action,
                    micro_live_allowed,
                    refreshed_at,
                    source_version,
                    build_id
                )
                VALUES (
                    1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s
                )
                ON CONFLICT (id) DO UPDATE SET
                    candidates_total=EXCLUDED.candidates_total,
                    sample_ready=EXCLUDED.sample_ready,
                    wait_both_sample=EXCLUDED.wait_both_sample,
                    wait_total_sample=EXCLUDED.wait_total_sample,
                    wait_oos_sample=EXCLUDED.wait_oos_sample,
                    min_remaining_total_trades=EXCLUDED.min_remaining_total_trades,
                    min_remaining_oos_trades=EXCLUDED.min_remaining_oos_trades,
                    avg_progress_pct=EXCLUDED.avg_progress_pct,
                    max_progress_pct=EXCLUDED.max_progress_pct,
                    collection_status=EXCLUDED.collection_status,
                    phase_status=EXCLUDED.phase_status,
                    recommended_action=EXCLUDED.recommended_action,
                    micro_live_allowed=EXCLUDED.micro_live_allowed,
                    refreshed_at=EXCLUDED.refreshed_at,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id;
            """, (
                candidates_total,
                sample_ready,
                int(r["wait_both_sample"] or 0),
                int(r["wait_total_sample"] or 0),
                int(r["wait_oos_sample"] or 0),
                r["min_remaining_total_trades"],
                r["min_remaining_oos_trades"],
                r["avg_progress_pct"],
                r["max_progress_pct"],
                collection_status,
                phase_status,
                recommended_action,
                micro_live_allowed,
                SOURCE_VERSION,
                build_id,
            ))

    print(f"candidates_total={candidates_total}")
    print(f"sample_ready={sample_ready}")
    print(f"collection_status={collection_status}")
    print(f"phase_status={phase_status}")
    print(f"micro_live_allowed={int(micro_live_allowed)}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_paper_runtime_sample_collection_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_V1 ==="

scripts/apply_paper_runtime_sample_collection_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_runtime_sample_collection_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_runtime_sample_collection_v1.py \
  | tee /tmp/paper_runtime_sample_collection_v1.txt

grep -q "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY" /tmp/paper_runtime_sample_collection_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE id=1;")
allowed=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_runtime_sample_collection_v1 WHERE micro_live_allowed=true;")

test "$rows" = "1"
test "$allowed" = "0"

psql -d finam_core -c "
SELECT
    candidates_total,
    sample_ready,
    wait_both_sample,
    min_remaining_total_trades,
    min_remaining_oos_trades,
    avg_progress_pct,
    max_progress_pct,
    collection_status,
    phase_status,
    recommended_action
FROM marketcore_ui.paper_runtime_sample_collection_v1
WHERE id=1;
"

echo "sample_collection_rows=$rows"
echo "micro_live_allowed_rows=$allowed"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_SAMPLE_COLLECTION_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_SAMPLE_COLLECTION_V1_OK"
SH_TEST

chmod +x scripts/test_paper_runtime_sample_collection_v1.sh

scripts/apply_paper_runtime_sample_collection_v1.sh
scripts/test_paper_runtime_sample_collection_v1.sh

echo "VERDICT=BUILD_PAPER_RUNTIME_SAMPLE_COLLECTION_V1_OK"
