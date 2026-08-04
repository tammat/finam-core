#!/usr/bin/env bash
set -euo pipefail

MARKET_SCRIPT="src/scripts/build_market_snapshot_history_backfill_v1.py"
FEATURE_SCRIPT="src/scripts/build_feature_snapshot_history_backfill_v1.py"

echo "=== TEST_FEATURE_STORE_INCREMENTAL_V1 ==="

for file in "$MARKET_SCRIPT" "$FEATURE_SCRIPT"
do
    [[ -f "$file" ]] || {
        echo "ERROR=missing_file:$file"
        exit 1
    }

    PYTHONPATH=src python -m py_compile "$file"
done

python3 - <<'PY'
from pathlib import Path

market = Path(
    "src/scripts/build_market_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

feature = Path(
    "src/scripts/build_feature_snapshot_history_backfill_v1.py"
).read_text(encoding="utf-8")

required_market = [
    '"incremental"',
    "FEATURE_STORE_OVERLAP_BARS",
    "max(20, args.overlap_bars)",
    "new_rows AS",
    "overlap_rows AS",
    "LIMIT %s",
    "--dry-run",
]

required_feature = [
    '"incremental"',
    "FEATURE_STORE_OVERLAP_BARS",
    "FEATURE_CONTEXT_BARS = 20",
    "max(20, args.overlap_bars)",
    "historical_context AS",
    "context_rank <= %s",
    "ROWS BETWEEN 19 PRECEDING",
    "WHERE output_row",
    "--dry-run",
]

for item in required_market:
    if item not in market:
        raise SystemExit(
            f"ERROR=market_contract_missing:{item}"
        )

for item in required_feature:
    if item not in feature:
        raise SystemExit(
            f"ERROR=feature_contract_missing:{item}"
        )

if 'DEFAULT_MODE = os.getenv(\n    "FEATURE_STORE_MODE",\n    "full"' in market:
    raise SystemExit("ERROR=market_default_full_mode")

if 'DEFAULT_MODE = os.getenv(\n    "FEATURE_STORE_MODE",\n    "full"' in feature:
    raise SystemExit("ERROR=feature_default_full_mode")

print("source_contract=OK")
PY

MARKET_HELP="$(
    PYTHONPATH=src python "$MARKET_SCRIPT" --help
)"

FEATURE_HELP="$(
    PYTHONPATH=src python "$FEATURE_SCRIPT" --help
)"

grep -q -- "--mode" <<<"$MARKET_HELP"
grep -q -- "--overlap-bars" <<<"$MARKET_HELP"
grep -q -- "--dry-run" <<<"$MARKET_HELP"

grep -q -- "--mode" <<<"$FEATURE_HELP"
grep -q -- "--overlap-bars" <<<"$FEATURE_HELP"
grep -q -- "--dry-run" <<<"$FEATURE_HELP"

echo
echo "=== MARKET SNAPSHOT DRY RUN ==="

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$MARKET_SCRIPT" \
    --dry-run |
    tee /tmp/market_snapshot_incremental_v1.log

grep -q \
    "mode=incremental" \
    /tmp/market_snapshot_incremental_v1.log

grep -q \
    "overlap_bars=20" \
    /tmp/market_snapshot_incremental_v1.log

grep -q \
    "dry_run=1" \
    /tmp/market_snapshot_incremental_v1.log

grep -q \
    "VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY" \
    /tmp/market_snapshot_incremental_v1.log

echo
echo "=== FEATURE SNAPSHOT DRY RUN ==="

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS=20 \
PYTHONPATH=src \
python "$FEATURE_SCRIPT" \
    --dry-run |
    tee /tmp/feature_snapshot_incremental_v1.log

grep -q \
    "mode=incremental" \
    /tmp/feature_snapshot_incremental_v1.log

grep -q \
    "overlap_bars=20" \
    /tmp/feature_snapshot_incremental_v1.log

grep -q \
    "context_bars=40" \
    /tmp/feature_snapshot_incremental_v1.log

grep -q \
    "dry_run=1" \
    /tmp/feature_snapshot_incremental_v1.log

grep -q \
    "VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY" \
    /tmp/feature_snapshot_incremental_v1.log

echo
echo "VERDICT=TEST_FEATURE_STORE_INCREMENTAL_V1_OK"
