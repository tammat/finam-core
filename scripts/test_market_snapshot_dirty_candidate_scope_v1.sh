#!/usr/bin/env bash
set -euo pipefail

FILE="src/scripts/build_market_snapshot_history_backfill_v1.py"

echo "=== TEST_MARKET_SNAPSHOT_DIRTY_CANDIDATE_SCOPE_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=source_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/build_market_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

required = [
    "new_rows AS",
    "overlap_rows AS",
    "incremental_source AS",
    "RETURNING symbol, timeframe",
    "market_dirty = true",
]

for token in required:
    if token not in text:
        raise SystemExit(
            f"ERROR=required_contract_missing:{token}"
        )

overlap_start = text.find("overlap_rows AS (")
overlap_end = text.find(
    "incremental_source AS (",
    overlap_start,
)

if overlap_start < 0:
    raise SystemExit(
        "ERROR=overlap_rows_block_missing"
    )

if overlap_end < 0:
    raise SystemExit(
        "ERROR=incremental_source_block_missing"
    )

overlap_block = text[overlap_start:overlap_end]

current_global_overlap = (
    "FROM watermark w" in overlap_block
)

candidate_overlap_present = (
    "FROM changed_scope scope" in overlap_block
    and "CROSS JOIN LATERAL" in overlap_block
)

required_candidate_contract = [
    "changed_scope AS",
    "FROM new_rows",
    "FROM changed_scope scope",
]

print(
    "global_overlap_scope_present="
    f"{int(current_global_overlap)}"
)
print(
    "candidate_overlap_scope_present="
    f"{int(candidate_overlap_present)}"
)

if current_global_overlap:
    raise SystemExit(
        "ERROR=MARKET_OVERLAP_STILL_GLOBAL"
    )

if not candidate_overlap_present:
    raise SystemExit(
        "ERROR=MARKET_OVERLAP_CANDIDATE_SCOPE_MISSING"
    )

for token in required_candidate_contract:
    if token not in text:
        raise SystemExit(
            f"ERROR=candidate_scope_contract_missing:{token}"
        )

print("status=MARKET_OVERLAP_CANDIDATE_SCOPED")
print("VERDICT=TEST_MARKET_SNAPSHOT_DIRTY_CANDIDATE_SCOPE_V1_OK")
PY
