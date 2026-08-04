#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
SOURCE_DIR="$ROOT/deploy/systemd"
TARGET_DIR="/etc/systemd/system"

UNITS=(
    "finam-feature-store-historical-correction-audit.service"
    "finam-feature-store-historical-correction-audit.timer"
    "finam-feature-store-historical-correction-retention.service"
    "finam-feature-store-historical-correction-retention.timer"
)

cd "$ROOT" || exit 1

echo "=== INSTALL_FEATURE_STORE_HISTORICAL_CORRECTION_SYSTEMD_V1 ==="

for unit in "${UNITS[@]}"
do
    [[ -f "$SOURCE_DIR/$unit" ]] || {
        echo "ERROR=unit_source_missing:$unit"
        exit 1
    }

    sudo install \
        -o root \
        -g root \
        -m 0644 \
        "$SOURCE_DIR/$unit" \
        "$TARGET_DIR/$unit"

    echo "installed_unit=$unit"
done

sudo systemctl daemon-reload

sudo systemctl enable \
    --now \
    finam-feature-store-historical-correction-audit.timer \
    finam-feature-store-historical-correction-retention.timer

echo "audit_timer_enabled=1"
echo "retention_timer_enabled=1"
echo "feature_store_timer_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
  "VERDICT=FEATURE_STORE_HISTORICAL_CORRECTION_SYSTEMD_V1_READY"
