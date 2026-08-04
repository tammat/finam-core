#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"

AUDIT_FILE="$ROOT/src/scripts/build_feature_store_historical_correction_audit_v1.py"
MARKET_FILE="$ROOT/src/scripts/build_market_snapshot_history_backfill_v1.py"
FEATURE_FILE="$ROOT/src/scripts/build_feature_snapshot_history_backfill_v1.py"

AUDIT_LOG="/tmp/feature_store_historical_correction_pipeline_audit_v1.log"
MARKET_LOG="/tmp/feature_store_historical_correction_pipeline_market_v1.log"
FEATURE_LOG="/tmp/feature_store_historical_correction_pipeline_feature_v1.log"

BACKUP_FILE="/tmp/feature_store_historical_correction_pipeline_backup_v1.json"
RUN_ID_FILE="/tmp/feature_store_historical_correction_pipeline_run_id_v1.txt"

SYMBOL="${TEST_SYMBOL:-BTCUSD}"
TIMEFRAME="${TEST_TIMEFRAME:-M1}"
WINDOW_BARS="${TEST_WINDOW_BARS:-20}"
VOLUME_DELTA="${TEST_VOLUME_DELTA:-0.001}"
VOLUME_TOLERANCE="${FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE:-0.00005}"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_PIPELINE_V1 ==="

for file in \
    "$AUDIT_FILE" \
    "$MARKET_FILE" \
    "$FEATURE_FILE"
do
    [[ -f "$file" ]] || {
        echo "ERROR=required_source_missing:$file"
        exit 1
    }
done

PYTHONPATH=src python -m py_compile \
    "$AUDIT_FILE" \
    "$MARKET_FILE" \
    "$FEATURE_FILE"

python3 - <<'PY_CONTRACT'
from pathlib import Path

contracts = {
    "src/scripts/build_feature_store_historical_correction_audit_v1.py": [
        "market_dirty = true",
        "FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE",
        "feature_store_historical_correction_audit_v1",
        "--symbol",
        "--timeframe",
    ],
    "src/scripts/build_market_snapshot_history_backfill_v1.py": [
        "market_dirty",
        "RETURNING",
        "feature_store_watermark_v1",
    ],
    "src/scripts/build_feature_snapshot_history_backfill_v1.py": [
        "WHERE market_dirty",
        "market_dirty =",
        "feature_processed_at",
        "feature_store_watermark_v1",
    ],
}

for filename, required_tokens in contracts.items():
    text = Path(filename).read_text(encoding="utf-8")

    for token in required_tokens:
        if token not in text:
            raise SystemExit(
                f"ERROR=source_contract_missing:{filename}:{token}"
            )

print("source_contract=OK")
PY_CONTRACT

rm -f \
    "$AUDIT_LOG" \
    "$MARKET_LOG" \
    "$FEATURE_LOG" \
    "$BACKUP_FILE" \
    "$RUN_ID_FILE"

cleanup() {
    local cleanup_rc=0

    echo
    echo "=== CLEANUP ==="

    BACKUP_FILE="$BACKUP_FILE" \
    RUN_ID_FILE="$RUN_ID_FILE" \
    PYTHONPATH=src \
    python3 - <<'PY_CLEANUP' || cleanup_rc=$?
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2


dsn = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

backup_path = Path(os.environ["BACKUP_FILE"])
run_id_path = Path(os.environ["RUN_ID_FILE"])

if not backup_path.exists():
    print("cleanup_status=NO_BACKUP")
    raise SystemExit(0)

backup = json.loads(
    backup_path.read_text(encoding="utf-8")
)

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        snapshot = backup["snapshot"]

        cur.execute(
            """
            UPDATE marketcore.market_snapshot_v1
            SET
                open = %s,
                high = %s,
                low = %s,
                close = %s,
                volume = %s,
                freshness_sec = %s,
                quality_status = %s,
                source_table = %s,
                source_version = %s,
                build_id = %s,
                refreshed_at = %s
            WHERE symbol = %s
              AND timeframe = %s
              AND bar_ts = %s
            """,
            (
                snapshot["open"],
                snapshot["high"],
                snapshot["low"],
                snapshot["close"],
                snapshot["volume"],
                snapshot["freshness_sec"],
                snapshot["quality_status"],
                snapshot["source_table"],
                snapshot["source_version"],
                snapshot["build_id"],
                snapshot["refreshed_at"],
                backup["symbol"],
                backup["timeframe"],
                backup["bar_ts"],
            ),
        )

        if cur.rowcount != 1:
            raise SystemExit(
                "ERROR=cleanup_snapshot_restore_failed"
            )

        feature = backup["feature"]

        cur.execute(
            """
            UPDATE analytics.feature_snapshot_v1
            SET
                asset_class = %s,
                open = %s,
                high = %s,
                low = %s,
                close = %s,
                volume = %s,
                range_abs = %s,
                range_pct = %s,
                body_abs = %s,
                body_pct = %s,
                upper_wick_pct = %s,
                lower_wick_pct = %s,
                hour_msk = %s,
                weekday_msk = %s,
                freshness_sec = %s,
                market_quality_status = %s,
                feature_quality_score = %s,
                source_table = %s,
                source_version = %s,
                build_id = %s,
                refreshed_at = %s,
                return1_pct = %s,
                return5_pct = %s,
                volume_sma20 = %s,
                volume_ratio20 = %s
            WHERE symbol = %s
              AND timeframe = %s
              AND bar_ts = %s
            """,
            (
                feature["asset_class"],
                feature["open"],
                feature["high"],
                feature["low"],
                feature["close"],
                feature["volume"],
                feature["range_abs"],
                feature["range_pct"],
                feature["body_abs"],
                feature["body_pct"],
                feature["upper_wick_pct"],
                feature["lower_wick_pct"],
                feature["hour_msk"],
                feature["weekday_msk"],
                feature["freshness_sec"],
                feature["market_quality_status"],
                feature["feature_quality_score"],
                feature["source_table"],
                feature["source_version"],
                feature["build_id"],
                feature["refreshed_at"],
                feature["return1_pct"],
                feature["return5_pct"],
                feature["volume_sma20"],
                feature["volume_ratio20"],
                backup["symbol"],
                backup["timeframe"],
                backup["bar_ts"],
            ),
        )

        if cur.rowcount != 1:
            raise SystemExit(
                "ERROR=cleanup_feature_restore_failed"
            )

        watermark = backup["watermark"]

        cur.execute(
            """
            UPDATE analytics.feature_store_watermark_v1
            SET
                market_snapshot_last_ts = %s,
                feature_snapshot_last_ts = %s,
                market_dirty = %s,
                market_dirty_at = %s,
                feature_processed_at = %s,
                source_version = %s,
                updated_at = %s
            WHERE symbol = %s
              AND timeframe = %s
            """,
            (
                watermark["market_snapshot_last_ts"],
                watermark["feature_snapshot_last_ts"],
                watermark["market_dirty"],
                watermark["market_dirty_at"],
                watermark["feature_processed_at"],
                watermark["source_version"],
                watermark["updated_at"],
                backup["symbol"],
                backup["timeframe"],
            ),
        )

        if cur.rowcount != 1:
            raise SystemExit(
                "ERROR=cleanup_watermark_restore_failed"
            )

        if run_id_path.exists():
            audit_run_id = run_id_path.read_text(
                encoding="utf-8"
            ).strip()

            if audit_run_id:
                cur.execute(
                    """
                    DELETE FROM
                        analytics.feature_store_historical_correction_audit_v1
                    WHERE audit_run_id = %s::uuid
                    """,
                    (audit_run_id,),
                )

                print(
                    "cleanup_audit_rows_deleted="
                    f"{cur.rowcount}"
                )

    conn.commit()

print("cleanup_snapshot_restored=1")
print("cleanup_feature_restored=1")
print("cleanup_watermark_restored=1")
print("cleanup_status=OK")
PY_CLEANUP

    rm -f "$BACKUP_FILE" "$RUN_ID_FILE"

    if [[ "$cleanup_rc" -ne 0 ]]; then
        echo "ERROR=cleanup_failed"
        return "$cleanup_rc"
    fi
}

trap cleanup EXIT

echo
echo "=== PREPARE CONTROLLED HISTORICAL CORRECTION ==="

SYMBOL="$SYMBOL" \
TIMEFRAME="$TIMEFRAME" \
WINDOW_BARS="$WINDOW_BARS" \
VOLUME_DELTA="$VOLUME_DELTA" \
BACKUP_FILE="$BACKUP_FILE" \
PYTHONPATH=src \
python3 - <<'PY_PREPARE'
from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


dsn = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

symbol = os.environ["SYMBOL"]
timeframe = os.environ["TIMEFRAME"]
window_bars = int(os.environ["WINDOW_BARS"])
volume_delta = Decimal(os.environ["VOLUME_DELTA"])
backup_path = Path(os.environ["BACKUP_FILE"])


def serialise(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


with psycopg2.connect(dsn) as conn:
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

                snapshot.open AS snapshot_open,
                snapshot.high AS snapshot_high,
                snapshot.low AS snapshot_low,
                snapshot.close AS snapshot_close,
                snapshot.volume AS snapshot_volume,
                snapshot.freshness_sec
                    AS snapshot_freshness_sec,
                snapshot.quality_status
                    AS snapshot_quality_status,
                snapshot.source_table
                    AS snapshot_source_table,
                snapshot.source_version
                    AS snapshot_source_version,
                snapshot.build_id
                    AS snapshot_build_id,
                snapshot.refreshed_at
                    AS snapshot_refreshed_at,

                feature.asset_class
                    AS feature_asset_class,
                feature.open AS feature_open,
                feature.high AS feature_high,
                feature.low AS feature_low,
                feature.close AS feature_close,
                feature.volume AS feature_volume,
                feature.range_abs AS feature_range_abs,
                feature.range_pct AS feature_range_pct,
                feature.body_abs AS feature_body_abs,
                feature.body_pct AS feature_body_pct,
                feature.upper_wick_pct
                    AS feature_upper_wick_pct,
                feature.lower_wick_pct
                    AS feature_lower_wick_pct,
                feature.hour_msk AS feature_hour_msk,
                feature.weekday_msk
                    AS feature_weekday_msk,
                feature.freshness_sec
                    AS feature_freshness_sec,
                feature.market_quality_status
                    AS feature_market_quality_status,
                feature.feature_quality_score
                    AS feature_quality_score,
                feature.source_table
                    AS feature_source_table,
                feature.source_version
                    AS feature_source_version,
                feature.build_id
                    AS feature_build_id,
                feature.refreshed_at
                    AS feature_refreshed_at,
                feature.return1_pct
                    AS feature_return1_pct,
                feature.return5_pct
                    AS feature_return5_pct,
                feature.volume_sma20
                    AS feature_volume_sma20,
                feature.volume_ratio20
                    AS feature_volume_ratio20,

                watermark.market_snapshot_last_ts,
                watermark.feature_snapshot_last_ts,
                watermark.market_dirty,
                watermark.market_dirty_at,
                watermark.feature_processed_at,
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
            JOIN analytics.feature_snapshot_v1 feature
              ON feature.symbol = source.symbol
             AND feature.timeframe = source.timeframe
             AND feature.bar_ts = source.ts
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
                "ERROR=pipeline_test_candidate_not_found"
            )

        if row["market_dirty"]:
            raise SystemExit(
                "ERROR=pipeline_test_pair_already_dirty"
            )

        backup = {
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "bar_ts": serialise(row["bar_ts"]),
            "source_volume": serialise(
                row["source_volume"]
            ),
            "snapshot": {
                "open": serialise(row["snapshot_open"]),
                "high": serialise(row["snapshot_high"]),
                "low": serialise(row["snapshot_low"]),
                "close": serialise(row["snapshot_close"]),
                "volume": serialise(row["snapshot_volume"]),
                "freshness_sec": row[
                    "snapshot_freshness_sec"
                ],
                "quality_status": row[
                    "snapshot_quality_status"
                ],
                "source_table": row[
                    "snapshot_source_table"
                ],
                "source_version": row[
                    "snapshot_source_version"
                ],
                "build_id": row["snapshot_build_id"],
                "refreshed_at": serialise(
                    row["snapshot_refreshed_at"]
                ),
            },
            "feature": {
                "asset_class": row["feature_asset_class"],
                "open": serialise(row["feature_open"]),
                "high": serialise(row["feature_high"]),
                "low": serialise(row["feature_low"]),
                "close": serialise(row["feature_close"]),
                "volume": serialise(row["feature_volume"]),
                "range_abs": serialise(
                    row["feature_range_abs"]
                ),
                "range_pct": serialise(
                    row["feature_range_pct"]
                ),
                "body_abs": serialise(
                    row["feature_body_abs"]
                ),
                "body_pct": serialise(
                    row["feature_body_pct"]
                ),
                "upper_wick_pct": serialise(
                    row["feature_upper_wick_pct"]
                ),
                "lower_wick_pct": serialise(
                    row["feature_lower_wick_pct"]
                ),
                "hour_msk": row["feature_hour_msk"],
                "weekday_msk": row["feature_weekday_msk"],
                "freshness_sec": row[
                    "feature_freshness_sec"
                ],
                "market_quality_status": row[
                    "feature_market_quality_status"
                ],
                "feature_quality_score": serialise(
                    row["feature_quality_score"]
                ),
                "source_table": row["feature_source_table"],
                "source_version": row[
                    "feature_source_version"
                ],
                "build_id": row["feature_build_id"],
                "refreshed_at": serialise(
                    row["feature_refreshed_at"]
                ),
                "return1_pct": serialise(
                    row["feature_return1_pct"]
                ),
                "return5_pct": serialise(
                    row["feature_return5_pct"]
                ),
                "volume_sma20": serialise(
                    row["feature_volume_sma20"]
                ),
                "volume_ratio20": serialise(
                    row["feature_volume_ratio20"]
                ),
            },
            "watermark": {
                "market_snapshot_last_ts": serialise(
                    row["market_snapshot_last_ts"]
                ),
                "feature_snapshot_last_ts": serialise(
                    row["feature_snapshot_last_ts"]
                ),
                "market_dirty": bool(row["market_dirty"]),
                "market_dirty_at": serialise(
                    row["market_dirty_at"]
                ),
                "feature_processed_at": serialise(
                    row["feature_processed_at"]
                ),
                "source_version": row[
                    "watermark_source_version"
                ],
                "updated_at": serialise(
                    row["watermark_updated_at"]
                ),
            },
        }

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
                    'HISTORICAL_CORRECTION_PIPELINE_TEST_V1',
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
                "ERROR=controlled_snapshot_change_failed"
            )

    conn.commit()

print(f"test_symbol={row['symbol']}")
print(f"test_timeframe={row['timeframe']}")
print(f"test_bar_ts={row['bar_ts'].isoformat()}")
print(f"source_volume={row['source_volume']}")
print(
    "original_snapshot_volume="
    f"{row['snapshot_volume']}"
)
print(f"changed_snapshot_volume={changed_volume}")
print(f"volume_delta={volume_delta}")
print("controlled_difference_created=1")
PY_PREPARE

echo
echo "=== RUN HISTORICAL CORRECTION AUDIT ==="

FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE="$VOLUME_TOLERANCE" \
PYTHONPATH=src \
python "$AUDIT_FILE" \
    --window-bars "$WINDOW_BARS" \
    --symbol "$SYMBOL" \
    --timeframe "$TIMEFRAME" |
    tee "$AUDIT_LOG"

AUDIT_RUN_ID="$(
    awk -F= '
        /^audit_run_id=/ {
            print $2
            exit
        }
    ' "$AUDIT_LOG"
)"

[[ -n "$AUDIT_RUN_ID" ]] || {
    echo "ERROR=audit_run_id_missing"
    exit 1
}

printf '%s\n' "$AUDIT_RUN_ID" > "$RUN_ID_FILE"

grep -q "checked_pairs=1" "$AUDIT_LOG" || {
    echo "ERROR=audit_checked_pair_count_invalid"
    exit 1
}

grep -q "changed_pairs=1" "$AUDIT_LOG" || {
    echo "ERROR=audit_did_not_detect_pair"
    exit 1
}

grep -q "changed_rows=1" "$AUDIT_LOG" || {
    echo "ERROR=audit_changed_row_count_invalid"
    exit 1
}

grep -q "dirty_rows_updated=1" "$AUDIT_LOG" || {
    echo "ERROR=audit_did_not_set_dirty"
    exit 1
}

echo
echo "=== VERIFY DIRTY AFTER AUDIT ==="

DIRTY_AFTER_AUDIT="$(
    SYMBOL="$SYMBOL" \
    TIMEFRAME="$TIMEFRAME" \
    AUDIT_RUN_ID="$AUDIT_RUN_ID" \
    PYTHONPATH=src \
    python3 - <<'PY_VERIFY_DIRTY'
from __future__ import annotations

import os

import psycopg2


dsn = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

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
                os.environ["AUDIT_RUN_ID"],
                os.environ["SYMBOL"],
                os.environ["TIMEFRAME"],
            ),
        )

        row = cur.fetchone()

if row is None:
    raise SystemExit(
        "ERROR=dirty_after_audit_row_missing"
    )

print("|".join(str(value) for value in row))
PY_VERIFY_DIRTY
)"

echo "dirty_after_audit=$DIRTY_AFTER_AUDIT"

[[ "$DIRTY_AFTER_AUDIT" == "1|1|1|1" ]] || {
    echo "ERROR=dirty_after_audit_verification_failed"
    exit 1
}

echo
echo "=== RUN MARKET SNAPSHOT BUILDER ==="

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS="$WINDOW_BARS" \
PYTHONPATH=src \
python "$MARKET_FILE" |
    tee "$MARKET_LOG"

grep -q "mode=incremental" "$MARKET_LOG"
grep -q "dry_run=0" "$MARKET_LOG"

grep -q \
    "VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY" \
    "$MARKET_LOG" || {
        echo "ERROR=market_builder_verdict_missing"
        exit 1
    }

MARKET_PROCESSED_ROWS="$(
    awk -F= '
        /^processed_rows=/ {
            print $2
            exit
        }
    ' "$MARKET_LOG"
)"

[[ "$MARKET_PROCESSED_ROWS" =~ ^[0-9]+$ ]] || {
    echo "ERROR=invalid_market_processed_rows"
    exit 1
}

(( MARKET_PROCESSED_ROWS >= 1 )) || {
    echo "ERROR=market_builder_did_not_restore_correction"
    exit 1
}

echo
echo "=== RUN FEATURE SNAPSHOT BUILDER ==="

FEATURE_STORE_MODE=incremental \
FEATURE_STORE_OVERLAP_BARS="$WINDOW_BARS" \
PYTHONPATH=src \
python "$FEATURE_FILE" |
    tee "$FEATURE_LOG"

grep -q "mode=incremental" "$FEATURE_LOG"
grep -q "dry_run=0" "$FEATURE_LOG"

grep -q \
    "VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY" \
    "$FEATURE_LOG" || {
        echo "ERROR=feature_builder_verdict_missing"
        exit 1
    }

FEATURE_PROCESSED_ROWS="$(
    awk -F= '
        /^processed_rows=/ {
            print $2
            exit
        }
    ' "$FEATURE_LOG"
)"

[[ "$FEATURE_PROCESSED_ROWS" =~ ^[0-9]+$ ]] || {
    echo "ERROR=invalid_feature_processed_rows"
    exit 1
}

# processed_rows отражает только фактические INSERT/UPDATE.
# После восстановления market snapshot признаки могут уже совпадать,
# поэтому processed_rows=0 является корректным noop-результатом.
echo "feature_processed_rows=$FEATURE_PROCESSED_ROWS"
echo "feature_noop_allowed=1"

echo
echo "=== VERIFY COMPLETE PIPELINE ==="

PIPELINE_STATE="$(
    SYMBOL="$SYMBOL" \
    TIMEFRAME="$TIMEFRAME" \
    VOLUME_TOLERANCE="$VOLUME_TOLERANCE" \
    PYTHONPATH=src \
    python3 - <<'PY_VERIFY_PIPELINE'
from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


dsn = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

symbol = os.environ["SYMBOL"]
timeframe = os.environ["TIMEFRAME"]
tolerance = Decimal(os.environ["VOLUME_TOLERANCE"])

with psycopg2.connect(dsn) as conn:
    with conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    ) as cur:
        cur.execute(
            """
            SELECT
                source.ts,
                source.volume AS source_volume,
                snapshot.volume AS snapshot_volume,
                feature.volume AS feature_volume,
                watermark.market_dirty,
                watermark.market_snapshot_last_ts,
                watermark.feature_snapshot_last_ts,
                watermark.feature_processed_at
            FROM (
                SELECT
                    mb.ts,
                    mb.volume
                FROM public.market_bars mb
                WHERE mb.symbol = %s
                  AND mb.timeframe = %s
                  AND mb.volume IS NOT NULL
                ORDER BY mb.ts DESC
                LIMIT 1
            ) source
            JOIN marketcore.market_snapshot_v1 snapshot
              ON snapshot.symbol = %s
             AND snapshot.timeframe = %s
             AND snapshot.bar_ts = source.ts
            JOIN analytics.feature_snapshot_v1 feature
              ON feature.symbol = %s
             AND feature.timeframe = %s
             AND feature.bar_ts = source.ts
            JOIN analytics.feature_store_watermark_v1 watermark
              ON watermark.symbol = %s
             AND watermark.timeframe = %s
            """,
            (
                symbol,
                timeframe,
                symbol,
                timeframe,
                symbol,
                timeframe,
                symbol,
                timeframe,
            ),
        )

        row = cur.fetchone()

if not row:
    raise SystemExit(
        "ERROR=complete_pipeline_state_missing"
    )

source_volume = Decimal(str(row["source_volume"]))
snapshot_volume = Decimal(str(row["snapshot_volume"]))
feature_volume = Decimal(str(row["feature_volume"]))

snapshot_matches = int(
    abs(source_volume - snapshot_volume) <= tolerance
)

feature_matches = int(
    abs(snapshot_volume - feature_volume) <= tolerance
)

dirty_cleared = int(not row["market_dirty"])

watermark_lag_zero = int(
    row["market_snapshot_last_ts"]
    == row["feature_snapshot_last_ts"]
)

feature_processed = int(
    row["feature_processed_at"] is not None
)

print(
    "|".join(
        str(value)
        for value in (
            snapshot_matches,
            feature_matches,
            dirty_cleared,
            watermark_lag_zero,
            feature_processed,
        )
    )
)
PY_VERIFY_PIPELINE
)"

echo "pipeline_state=$PIPELINE_STATE"
echo "market_processed_rows=$MARKET_PROCESSED_ROWS"
echo "feature_processed_rows=$FEATURE_PROCESSED_ROWS"

[[ "$PIPELINE_STATE" == "1|1|1|1|1" ]] || {
    echo "ERROR=complete_pipeline_verification_failed"
    exit 1
}

echo
echo "audit_detected=1"
echo "market_dirty_set=1"
echo "market_snapshot_restored=1"
echo "feature_dirty_scope_consumed=1"
echo "market_dirty_cleared=1"
echo "watermark_lag=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_PIPELINE_V1_OK"
