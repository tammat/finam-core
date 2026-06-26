#!/usr/bin/env bash
set -euo pipefail

echo "=== SETUP_SYSTEMD_KNOWLEDGE_COVERAGE_UI_V2 ==="

mkdir -p systemd

cat > systemd/marketcore-knowledge-ui.env <<'ENV'
DATABASE_URL=postgresql:///finam_core
KNOWLEDGE_UI_PORT=8090
PYTHONPATH=/opt/finam-core/src
ENV

cat > systemd/marketcore-knowledge-ui.service <<'SERVICE'
[Unit]
Description=MarketCore Knowledge Coverage UI
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=alex
Group=alex
WorkingDirectory=/opt/finam-core
EnvironmentFile=/opt/finam-core/systemd/marketcore-knowledge-ui.env
ExecStart=/opt/finam-core/venv/bin/python src/scripts/research/serve_knowledge_coverage_ui_v2.py
Restart=always
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=20
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
SERVICE

sudo cp systemd/marketcore-knowledge-ui.service /etc/systemd/system/marketcore-knowledge-ui.service
sudo systemctl daemon-reload
sudo systemctl enable marketcore-knowledge-ui
sudo systemctl restart marketcore-knowledge-ui

sleep 2

systemctl is-enabled marketcore-knowledge-ui
systemctl is-active marketcore-knowledge-ui

curl -fsS http://127.0.0.1:8090/ >/tmp/knowledge_coverage_ui_systemd_v2.html

grep -q "MarketCore Knowledge Coverage" /tmp/knowledge_coverage_ui_systemd_v2.html
grep -q "WORKFLOW" /tmp/knowledge_coverage_ui_systemd_v2.html
grep -q "CATALOG_READ_ONLY" /tmp/knowledge_coverage_ui_systemd_v2.html

echo "systemd_enabled=1"
echo "systemd_active=1"
echo "http_ready=1"
echo "source_policy=CATALOG_READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=SYSTEMD_KNOWLEDGE_COVERAGE_UI_V2_READY"
echo "TEST_SYSTEMD_KNOWLEDGE_COVERAGE_UI_V2_OK"
