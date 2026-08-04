#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
FILE="$ROOT/src/scripts/build_feature_store_historical_correction_audit_v1.py"
LOG="/tmp/feature_store_historical_correction_dirty_detection_v1.log"
BACKUP="/tmp/feature_store_historical_correction_dirty_detection_v1.json"
RUN_ID_FILE="/tmp/feature_store_historical_correction_dirty_detection_run_id_v1.txt"

SYMBOL="${TEST_SYMBOL:-BTCUSD}"
TIMEFRAME="${TEST_TIMEFRAME:-M1}"
WINDOW_BARS="${TEST_WINDOW_BARS:-20}"
VOLUME_DELTA="${TEST_VOLUME_DELTA:-0.001}"
VOLUME_TOLERANCE="${FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE:-0.00005}"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_DIRTY_DETECTION_V1 ==="

[[ -f "$FILE" ]] || {
    echo "ERROR=audit_builder_missing"
    exit 1
}

PYTHONPATH=src python -m py_compile "$FILE"

python3 - <<'PY'
from pathlib import Path

text = Path(
    "src/scripts/"
    "build_feature_store_historical_correction_audit_v1.py"
).read_text(encoding="utf-8")

required = [
    "FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE",
    "market_dirty = true",
    "feature_store_historical_correction_audit_v1",
    "--symbol",
    "--timeframe",
    "--window-bars",
]

for token in required:
    if token not in text:
        raise SystemExit(
            f"ERROR=required_contract_missing:{token}"
        )

print("source_contract=OK")
PY

rm -f "$BACKUP" "$RUN_ID_FILE" "$LOG"

cleanup() {
    local cleanup_rc=0

    echo
    echo "=== CLEANUP ==="

    BACKUP="$BACKUP" \
    RUN_ID_FILE="$RUN_ID_FILE" \
    PYTHONPATH=src \
    python3 - <<'PY' || cleanup_rc=$?
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2


db = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

backup_path = Path(os.environ["BACKUP"])
run_id_path = Path(os.environ["RUN_ID_FILE"])

if not backup_path.exists():
    print("cleanup_status=NO_BACKUP")
    raise SystemExit(0)

backup = json.loads(
    backup_path.read_text(encoding="utf-8")
)

with psycopg2.connect(db) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE marketcore.market_snapshot_v1
            SET
                volume = %s,
                source_version = %s,
                build_id = %s,
                refreshed_at = %s
            WHERE symbol = %s
              AND timeframe = %s
              AND bar_ts = %s
            """,
            (
                backup["snapshot_volume"],
                backup["snapshot_source_version"],
                backup["snapshot_build_id"],
                backup["snapshot_refreshed_at"],
                backup["symbol"],
                backup["timeframe"],
                backup["bar_ts"],
            ),
        )

        if cur.rowcount != 1:
            raise SystemExit(
                "ERROR=cleanup_snapshot_restore_failed"
            )

        cur.execute(
            """
            UPDATE analytics.feature_store_watermark_v1
            SET
                market_dirty = %s,
                market_dirty_at = %s,
                source_version = %s,
                updated_at = %s
            WHERE symbol = %s
              AND timeframe = %s
            """,
            (
                backup["market_dirty"],
                backup["market_dirty_at"],
                backup["watermark_source_version"],
                backup["watermark_updated_at"],
                backup["symbol"],
                backup["timeframe"],
            ),
        )

        if cur.rowcount != 1:
            raise SystemExit(
                "ERROR=cleanup_watermark_restore_failed"
            )

        if run_id_path.exists():
            run_id = run_id_path.read_text(
                encoding="utf-8"
            ).strip()

            if run_id:
                cur.execute(
                    """
                    DELETE FROM
                        analytics.feature_store_historical_correction_audit_v1
                    WHERE audit_run_id = %s::uuid
                    """,
                    (run_id,),
                )

                print(
                    "cleanup_audit_rows_deleted="
                    f"{cur.rowcount}"
                )

    conn.commit()

print("cleanup_snapshot_restored=1")
print("cleanup_watermark_restored=1")
print("cleanup_status=OK")
PY

    rm -f "$BACKUP" "$RUN_ID_FILE"

    if [[ "$cleanup_rc" -ne 0 ]]; then
        echo "ERROR=cleanup_failed"
        return "$cleanup_rc"
    fi
}

trap cleanup EXIT

echo
echo "=== PREPARE CONTROLLED DIFFERENCE ==="

SYMBOL="$SYMBOL" \
TIMEFRAME="$TIMEFRAME" \
WINDOW_BARS="$WINDOW_BARS" \
VOLUME_DELTA="$VOLUME_DELTA" \
BACKUP="$BACKUP" \
PYTHONPATH=src \
python3 - <<'PY'
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras


db = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

symbol = os.environ["SYMBOL"]
timeframe = os.environ["TIMEFRAME"]
window_bars = int(os.environ["WINDOW_BARS"])
volume_delta = Decimal(os.environ["VOLUME_DELTA"])
backup_path = Path(os.environ["BACKUP"])

with psycopg2.connect(db) as conn:
    with conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        cur.execute(
            """
            SELECT
                source.symbol,
                source.timeframe,
                source.ts AS bar_ts,
                source.volume AS source_volume,
                snapshot.volume AS snapshot_volume,
                snapshot.source_version
                    AS snapshot_source_version,
                snapshot.build_id
                    AS snapshot_build_id,
                snapshot.refreshed_at
                    AS snapshot_refreshed_at,
                watermark.market_dirty,
                watermark.market_dirty_at,
                watermark.source_version
                    AS watermark_source_version,
                watermark.updated_at
                    AS watermark_updated_at
            FROM (
                SELECT
                    mb.symbol,
                    mb.timeframe,
                    mb.ts,
                    mb.volume
                FROM public.market_bars mb
                WHERE mb.symbol = %s
                  AND mb.timeframe = %s
                  AND mb.volume IS NOT NULL
                ORDER BY mb.ts DESC
                LIMIT %s
            ) source
            JOIN marketcore.market_snapshot_v1 snapshot
              ON snapshot.symbol = source.symbol
             AND snapshot.timeframe = source.timeframe
             AND snapshot.bar_ts = source.ts
            JOIN analytics.feature_store_watermark_v1 watermark
              ON watermark.symbol = source.symbol
             AND watermark.timeframe = source.timeframe
            ORDER BY source.ts DESC
            LIMIT 1
            """,
            (
                symbol,
                timeframe,
                window_bars,
            ),
        )

        row = cur.fetchone()

        if not row:
            raise SystemExit(
                "ERROR=test_candidate_row_not_found"
            )

        if row["market_dirty"]:
            raise SystemExit(
                "ERROR=test_pair_already_dirty"
            )

        backup = {
            key: (
                value.isoformat()
                if hasattr(value, "isoformat")
                else str(value)
                if value is not None
                else None
            )
            for key, value in dict(row).items()
        }

        backup["market_dirty"] = bool(
            row["market_dirty"]
        )

        backup_path.write_text(
            json.dumps(
                backup,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        changed_volume = (
            Decimal(str(row["snapshot_volume"]))
            + volume_delta
        )

        cur.execute(
            """
            UPDATE marketcore.market_snapshot_v1
            SET
                volume = %s,
                source_version =
                    'HISTORICAL_CORRECTION_TEST_V1',
                refreshed_at = clock_timestamp()
            WHERE symbol = %s
              AND timeframe = %s
              AND bar_ts = %s
            """,
            (
                changed_volume,
                row["symbol"],
                row["timeframe"],
                row["bar_ts"],
            ),
        )

        if cur.rowcount != 1:
            raise SystemExit(
                "ERROR=controlled_snapshot_update_failed"
            )

    conn.commit()

print(f"test_symbol={row['symbol']}")
print(f"test_timeframe={row['timeframe']}")
print(f"test_bar_ts={row['bar_ts'].isoformat()}")
print(f"source_volume={row['source_volume']}")
print(f"original_snapshot_volume={row['snapshot_volume']}")
print(f"changed_snapshot_volume={changed_volume}")
print(f"volume_delta={volume_delta}")
print("controlled_difference_created=1")
PY

echo
echo "=== RUN HISTORICAL CORRECTION AUDIT ==="

FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE="$VOLUME_TOLERANCE" \
PYTHONPATH=src \
python "$FILE" \
    --window-bars "$WINDOW_BARS" \
    --symbol "$SYMBOL" \
    --timeframe "$TIMEFRAME" |
    tee "$LOG"

AUDIT_RUN_ID="$(
    awk -F= '
        /^audit_run_id=/ {
            print $2
            exit
        }
    ' "$LOG"
)"

[[ -n "$AUDIT_RUN_ID" ]] || {
    echo "ERROR=audit_run_id_missing"
    exit 1
}

printf '%s\n' "$AUDIT_RUN_ID" > "$RUN_ID_FILE"

grep -q "checked_pairs=1" "$LOG" || {
    echo "ERROR=unexpected_checked_pair_count"
    exit 1
}

grep -q "changed_pairs=1" "$LOG" || {
    echo "ERROR=controlled_difference_not_detected"
    exit 1
}

grep -q "changed_rows=1" "$LOG" || {
    echo "ERROR=unexpected_changed_row_count"
    exit 1
}

grep -q "dirty_rows_updated=1" "$LOG" || {
    echo "ERROR=dirty_row_not_updated"
    exit 1
}

grep -q "dry_run=0" "$LOG" || {
    echo "ERROR=audit_not_executed_in_write_mode"
    exit 1
}

grep -q \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_AUDIT_V1_READY" \
  "$LOG" || {
    echo "ERROR=audit_success_verdict_missing"
    exit 1
}

echo
echo "=== VERIFY DIRTY STATE ==="

VERIFY="$(
    SYMBOL="$SYMBOL" \
    TIMEFRAME="$TIMEFRAME" \
    AUDIT_RUN_ID="$AUDIT_RUN_ID" \
    PYTHONPATH=src \
    python3 - <<'PY_VERIFY'
from __future__ import annotations

import os

import psycopg2


dsn = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

symbol = os.environ["SYMBOL"]
timeframe = os.environ["TIMEFRAME"]
audit_run_id = os.environ["AUDIT_RUN_ID"]

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                w.market_dirty::integer,
                count(a.audit_id)::integer,
                coalesce(max(a.changed_rows), 0)::integer,
                coalesce(
                    bool_or(a.correction_detected),
                    false
                )::integer
            FROM analytics.feature_store_watermark_v1 w
            LEFT JOIN
                analytics.feature_store_historical_correction_audit_v1 a
              ON a.symbol = w.symbol
             AND a.timeframe = w.timeframe
             AND a.audit_run_id = %s::uuid
            WHERE w.symbol = %s
              AND w.timeframe = %s
            GROUP BY w.market_dirty
            """,
            (
                audit_run_id,
                symbol,
                timeframe,
            ),
        )
        row = cur.fetchone()

if row is None:
    raise SystemExit(
        "ERROR=dirty_verification_row_missing"
    )

print("|".join(str(value) for value in row))
PY_VERIFY
)"

echo "verification=$VERIFY"

[[ "$VERIFY" == "1|1|1|1" ]] || {
    echo "ERROR=dirty_audit_verification_failed:$VERIFY"
    exit 1
}

echo "audit_run_id=$AUDIT_RUN_ID"
echo "market_dirty_after_audit=1"
echo "audit_rows=1"
echo "changed_rows=1"
echo "controlled_restore_required=1"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_DIRTY_DETECTION_V1_OK"
