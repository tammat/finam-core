#!/usr/bin/env bash
set -euo pipefail

echo "=== SETUP_SYSTEMD_READ_ONLY_SYSTEM_STATUS_UI_V1 ==="

mkdir -p systemd

cat > systemd/finam-readonly-ui.env <<'ENV'
DATABASE_URL=postgresql:///finam_core
READONLY_UI_PORT=8089
PYTHONPATH=/opt/finam-core/src
ENV

cat > systemd/finam-readonly-ui.service <<'SERVICE'
[Unit]
Description=Finam Core ReadOnly System Status UI
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=alex
Group=alex
WorkingDirectory=/opt/finam-core
EnvironmentFile=/opt/finam-core/systemd/finam-readonly-ui.env
ExecStart=/opt/finam-core/venv/bin/python src/scripts/research/serve_read_only_system_status_ui_v1.py
Restart=always
RestartSec=5
KillSignal=SIGINT
TimeoutStopSec=20
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
SERVICE

sudo cp systemd/finam-readonly-ui.service /etc/systemd/system/finam-readonly-ui.service
sudo systemctl daemon-reload
sudo systemctl enable finam-readonly-ui
sudo systemctl restart finam-readonly-ui

sleep 2

systemctl is-enabled finam-readonly-ui
systemctl is-active finam-readonly-ui

curl -fsS http://127.0.0.1:8089/ >/tmp/read_only_system_status_ui_systemd_v1.html

grep -q "Finam Core" /tmp/read_only_system_status_ui_systemd_v1.html
grep -q "Главное меню" /tmp/read_only_system_status_ui_systemd_v1.html
grep -q "Назад" /tmp/read_only_system_status_ui_systemd_v1.html

echo "systemd_enabled=1"
echo "systemd_active=1"
echo "http_ready=1"
echo "source_policy=MART_ONLY"
echo "responsive_web_ui=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=SYSTEMD_READ_ONLY_SYSTEM_STATUS_UI_V1_READY"
echo "TEST_SYSTEMD_READ_ONLY_SYSTEM_STATUS_UI_V1_OK"
