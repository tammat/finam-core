#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${DB_NAME:-finam_core}"
LOG="runtime/audits/feature_store_candidate_scope_performance_v1.log"

echo "=== TEST_FEATURE_STORE_CANDIDATE_SCOPE_PERFORMANCE_V1 ==="

mkdir -p "$(dirname "$LOG")"

psql -X -d "$DB_NAME" -AtF $'\t' -c "
SELECT
    calls,
    rows,
    round(mean_exec_time::numeric, 2),
    shared_blks_read,
    temp_blks_written,
    regexp_replace(query, E'[\\n\\r\\t ]+', ' ', 'g')
FROM pg_stat_statements
WHERE query ILIKE '%changed_scope AS%'
  AND query ILIKE '%INSERT INTO marketcore.market_snapshot_v1%'
ORDER BY total_exec_time DESC
LIMIT 1;
" | tee "$LOG"

ROW="$(cat "$LOG")"

[[ -n "$ROW" ]] || {
    echo "ERROR=candidate_scope_statement_not_found"
    exit 1
}

IFS=$'\t' read -r \
  CALLS \
  ROWS \
  MEAN_MS \
  READ_BLOCKS \
  TEMP_BLOCKS \
  QUERY <<< "$ROW"

echo "calls=$CALLS"
echo "rows=$ROWS"
echo "mean_exec_ms=$MEAN_MS"
echo "shared_blks_read=$READ_BLOCKS"
echo "temp_blks_written=$TEMP_BLOCKS"

[[ "$CALLS" -ge 3 ]] || {
    echo "ERROR=insufficient_measurement_calls:$CALLS"
    exit 1
}

[[ "$TEMP_BLOCKS" -eq 0 ]] || {
    echo "ERROR=temp_writes_present:$TEMP_BLOCKS"
    exit 1
}

python3 - "$MEAN_MS" "$READ_BLOCKS" <<'PY'
from decimal import Decimal
import sys

mean_ms = Decimal(sys.argv[1])
read_blocks = int(sys.argv[2])

if mean_ms >= Decimal("500"):
    raise SystemExit(
        f"ERROR=mean_exec_time_too_high:{mean_ms}"
    )

if read_blocks >= 50000:
    raise SystemExit(
        f"ERROR=read_amplification_too_high:{read_blocks}"
    )

print("performance_thresholds=OK")
PY

echo "log_file=$LOG"
echo "VERDICT=TEST_FEATURE_STORE_CANDIDATE_SCOPE_PERFORMANCE_V1_OK"
