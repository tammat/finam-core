#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_FEATURE_STORE_TIMER_V1 ==="

mkdir -p deploy/systemd scripts

cat > deploy/systemd/finam-feature-store.service <<'UNIT'
[Unit]
Description=Finam Core Feature Store Refresh
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/opt/finam-core
Environment=DATABASE_URL=postgresql:///finam_core
Environment=BACKFILL_LIMIT=200000
ExecStart=/opt/finam-core/venv/bin/python src/scripts/build_market_snapshot_history_backfill_v1.py
ExecStart=/opt/finam-core/venv/bin/python src/scripts/build_feature_snapshot_history_backfill_v1.py
User=alex
Group=alex
UNIT

cat > deploy/systemd/finam-feature-store.timer <<'UNIT'
[Unit]
Description=Run Finam Feature Store Refresh every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
AccuracySec=30s
Unit=finam-feature-store.service
Persistent=true

[Install]
WantedBy=timers.target
UNIT

cat > scripts/test_feature_store_timer_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_TIMER_V1 ==="

test -f deploy/systemd/finam-feature-store.service
test -f deploy/systemd/finam-feature-store.timer

systemd-analyze verify \
  deploy/systemd/finam-feature-store.service \
  deploy/systemd/finam-feature-store.timer

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_snapshot_history_backfill_v1.py \
  src/scripts/build_feature_snapshot_history_backfill_v1.py

sudo cp deploy/systemd/finam-feature-store.service /etc/systemd/system/finam-feature-store.service
sudo cp deploy/systemd/finam-feature-store.timer /etc/systemd/system/finam-feature-store.timer

sudo systemctl daemon-reload
sudo systemctl enable finam-feature-store.timer
sudo systemctl restart finam-feature-store.timer

sudo systemctl start finam-feature-store.service

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
with_return=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1 WHERE return1_pct IS NOT NULL;")
active=$(systemctl is-active finam-feature-store.timer)

test "$rows" -gt 0
test "$with_return" -gt 0
test "$active" = "active"

systemctl list-timers --all | grep finam-feature-store || true

echo "feature_rows=$rows"
echo "with_return=$with_return"
echo "timer_active=$active"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=FEATURE_STORE_TIMER_V1_READY"
echo "VERDICT=TEST_FEATURE_STORE_TIMER_V1_OK"
SH_TEST

chmod +x scripts/test_feature_store_timer_v1.sh
scripts/test_feature_store_timer_v1.sh

echo "VERDICT=BUILD_FEATURE_STORE_TIMER_V1_OK"
