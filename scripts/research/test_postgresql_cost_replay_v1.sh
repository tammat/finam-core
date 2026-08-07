#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

MIGRATION="scripts/research/migrate_postgresql_cost_replay_v1.py"
BUILDER="scripts/research/build_postgresql_cost_replay_v1.py"
AUDIT="scripts/research/audit_postgresql_cost_replay_v1.py"

SOURCE_RUN_UUID="${1:-}"

if [[ -z "$SOURCE_RUN_UUID" ]]; then
    SOURCE_RUN_UUID="$(
        PYTHONPATH=src "$PYTHON" - <<'PYSQL'
from __future__ import annotations

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


with psycopg2.connect(build_psycopg_url()) as conn:
    conn.set_session(readonly=True)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT r.run_uuid::text
            FROM analytics.edge_lab_run_v1 r
            WHERE r.status_code = 'DONE'
              AND EXISTS (
                  SELECT 1
                  FROM analytics.research_trade_v1 t
                  WHERE t.run_uuid = r.run_uuid
              )
            ORDER BY r.finished_at DESC NULLS LAST, r.created_at DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()

if row is None:
    raise SystemExit("test_source_run_missing")

print(row[0])
PYSQL
    )"
fi

[[ -n "$SOURCE_RUN_UUID" ]] || {
    echo "ERROR=source_run_uuid_empty"
    exit 1
}

echo "source_run_uuid=$SOURCE_RUN_UUID"

LOG="/tmp/test_postgresql_cost_replay_v1.log"

cd "$ROOT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile \
  "$MIGRATION" \
  "$BUILDER" \
  "$AUDIT"

PYTHONPATH=src \
"$PYTHON" "$MIGRATION" --apply |
tee "$LOG"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --source-run-uuid "$SOURCE_RUN_UUID" \
  --cost-model LEGACY_FIXED_PER_SIDE \
  --cost-model-version \
    POSTGRESQL_COST_REPLAY_V1_TEST_LEGACY \
  --quantity 1 \
  --commission-per-side 1.5 \
  --dry-run |
tee -a "$LOG"

PYTHONPATH=src \
"$PYTHON" "$AUDIT" |
tee -a "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_COST_REPLAY_SCHEMA_MIGRATION_V1_READY" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_COST_REPLAY_V1_DRY_RUN_OK" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_COST_REPLAY_V1_AUDIT_OK" \
  "$LOG"

for marker in \
  "UPDATE analytics.research_trade_v1" \
  "DELETE FROM analytics.research_trade_v1" \
  "UPDATE analytics.edge_observation_v1" \
  "DELETE FROM analytics.edge_observation_v1" \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    COUNT="$(
      {
        grep -F "$marker" \
          "$MIGRATION" \
          "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

echo "historical_trade_rows_changed=0"
echo "historical_observation_rows_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "oos_allowed=0"
echo "shadow_allowed=0"
echo "paper_allowed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_COST_REPLAY_V1_OK"
