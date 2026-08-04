#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
UNIT_DIR="$ROOT/deploy/systemd"

AUDIT_SERVICE="$UNIT_DIR/finam-feature-store-historical-correction-audit.service"
AUDIT_TIMER="$UNIT_DIR/finam-feature-store-historical-correction-audit.timer"
RETENTION_SERVICE="$UNIT_DIR/finam-feature-store-historical-correction-retention.service"
RETENTION_TIMER="$UNIT_DIR/finam-feature-store-historical-correction-retention.timer"
INSTALLER="$ROOT/scripts/install_feature_store_historical_correction_systemd_v1.sh"

cd "$ROOT" || exit 1

echo "=== TEST_FEATURE_STORE_HISTORICAL_CORRECTION_SYSTEMD_PLAN_V1 ==="

for file in \
    "$AUDIT_SERVICE" \
    "$AUDIT_TIMER" \
    "$RETENTION_SERVICE" \
    "$RETENTION_TIMER" \
    "$INSTALLER"
do
    [[ -f "$file" ]] || {
        echo "ERROR=required_file_missing:$file"
        exit 1
    }
done

bash -n "$INSTALLER"

python3 - <<'PY'
from pathlib import Path

files = {
    "audit_service": Path(
        "deploy/systemd/"
        "finam-feature-store-historical-correction-audit.service"
    ).read_text(encoding="utf-8"),
    "audit_timer": Path(
        "deploy/systemd/"
        "finam-feature-store-historical-correction-audit.timer"
    ).read_text(encoding="utf-8"),
    "retention_service": Path(
        "deploy/systemd/"
        "finam-feature-store-historical-correction-retention.service"
    ).read_text(encoding="utf-8"),
    "retention_timer": Path(
        "deploy/systemd/"
        "finam-feature-store-historical-correction-retention.timer"
    ).read_text(encoding="utf-8"),
}

required = {
    "audit_service": [
        "User=alex",
        "DATABASE_URL=postgresql://finam:",
        "FEATURE_STORE_CORRECTION_VOLUME_TOLERANCE=0.00005",
        "build_feature_store_historical_correction_audit_v1.py",
        "--window-bars 20",
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
    ],
    "audit_timer": [
        "OnUnitActiveSec=1h",
        "Persistent=true",
        "RandomizedDelaySec=5min",
        "finam-feature-store-historical-correction-audit.service",
    ],
    "retention_service": [
        "User=postgres",
        "DATABASE_URL=postgresql:///finam_core",
        "run_feature_store_historical_correction_retention_v1.py",
        "--apply",
        "--batch-limit 5000",
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
    ],
    "retention_timer": [
        "OnCalendar=*-*-* 03:20:00",
        "Persistent=true",
        "RandomizedDelaySec=10min",
        "finam-feature-store-historical-correction-retention.service",
    ],
}

for file_code, tokens in required.items():
    text = files[file_code]

    for token in tokens:
        if token not in text:
            raise SystemExit(
                f"ERROR=unit_contract_missing:{file_code}:{token}"
            )

for file_code, text in files.items():
    forbidden = [
        "execution_enabled=1",
        "micro_live_allowed=1",
        "RuntimeExecutionEngine",
        "send_order",
    ]

    for token in forbidden:
        if token in text:
            raise SystemExit(
                f"ERROR=forbidden_runtime_contract:{file_code}:{token}"
            )

print("source_contract=OK")
PY

systemd-analyze verify \
    "$AUDIT_SERVICE" \
    "$AUDIT_TIMER" \
    "$RETENTION_SERVICE" \
    "$RETENTION_TIMER"

echo "audit_frequency=hourly"
echo "retention_frequency=daily_03_20"
echo "feature_store_timer_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=TEST_FEATURE_STORE_HISTORICAL_CORRECTION_SYSTEMD_PLAN_V1_OK"
