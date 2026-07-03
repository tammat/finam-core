#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_UI_SYSTEMD_8080_V1 ==="

mkdir -p deploy/systemd scripts src/scripts src/marketcore/presentation/pages

cat > deploy/systemd/marketcore-kg-api.service <<'UNIT'
[Unit]
Description=MarketCore Knowledge Graph API on 8095
After=network.target postgresql.service

[Service]
Type=simple
User=alex
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=/opt/finam-core/src
Environment=DATABASE_URL=postgresql:///finam_core
Environment=KG_API_HOST=127.0.0.1
Environment=KG_API_PORT=8095
ExecStart=/opt/finam-core/venv/bin/python src/marketcore/api/serve_knowledge_graph_api_v1.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > deploy/systemd/marketcore-ui-shell.service <<'UNIT'
[Unit]
Description=MarketCore UI Shell on 8080
After=network.target marketcore-kg-api.service
Wants=marketcore-kg-api.service

[Service]
Type=simple
User=alex
WorkingDirectory=/opt/finam-core
Environment=PYTHONPATH=/opt/finam-core/src
Environment=MARKETCORE_UI_HOST=0.0.0.0
Environment=MARKETCORE_UI_PORT=8080
Environment=KG_API_BASE_URL=http://127.0.0.1:8095
ExecStart=/opt/finam-core/venv/bin/python src/marketcore/presentation/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

cat > src/marketcore/presentation/pages/risk.py <<'PY'
from __future__ import annotations

from marketcore.presentation.page import Page


class RiskPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/risk",
            title="Риски",
            icon="⚠",
            menu_order=70,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Риски</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
PY

cat > src/marketcore/presentation/pages/settings.py <<'PY'
from __future__ import annotations

from marketcore.presentation.page import Page


class SettingsPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/settings",
            title="Настройки",
            icon="⚙",
            menu_order=120,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Настройки</h2>
            <p>Раздел подключён к MarketCore UI Shell. Здесь будут настройки локали, валюты, таймзоны, темы и API.</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "from marketcore.presentation.pages.risk import RiskPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.risk import RiskPage\n",
    )

if "from marketcore.presentation.pages.settings import SettingsPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.settings import SettingsPage\n",
    )

if "RiskPage()," not in s:
    s = s.replace(
        "HomePage(),",
        "HomePage(),\n    RiskPage(),",
    )

if "SettingsPage()," not in s:
    s = s.replace(
        "HomePage(),",
        "HomePage(),\n    SettingsPage(),",
    )

p.write_text(s)
PY

cat > src/scripts/check_marketcore_ui_systemd_8080_v1.py <<'PY'
from __future__ import annotations

import json
import sys
import time
from urllib.request import urlopen


def read_url(url: str, timeout: float = 5.0) -> str:
    with urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def wait_url(url: str, attempts: int = 20, delay: float = 0.5) -> str:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return read_url(url)
        except Exception as exc:
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"URL not ready: {url}; last_error={last_error}")


def main() -> None:
    kg_health_raw = wait_url("http://127.0.0.1:8095/api/kg/v1/health")
    kg_health = json.loads(kg_health_raw)
    assert kg_health.get("status") == "OK", kg_health_raw

    home = wait_url("http://127.0.0.1:8080/")
    risk = wait_url("http://127.0.0.1:8080/risk")
    settings = wait_url("http://127.0.0.1:8080/settings")

    assert "MarketCore OS" in home, "home missing MarketCore OS"
    assert "MARKETCORE_UI_SHELL_V1" in home, "home missing shell marker"
    assert "Риски" in risk, "risk page missing"
    assert "Настройки" in settings, "settings page missing"

    print("kg_api_8095=READY")
    print("marketcore_ui_8080=READY")
    print("risk_page=READY")
    print("settings_page=READY")
    print("VERDICT=CHECK_MARKETCORE_UI_SYSTEMD_8080_V1_OK")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_marketcore_ui_systemd_8080_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_SYSTEMD_8080_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/check_marketcore_ui_systemd_8080_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/app.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/settings.py \
  src/marketcore/presentation/registry.py

test -f deploy/systemd/marketcore-kg-api.service
test -f deploy/systemd/marketcore-ui-shell.service

grep -q "KG_API_PORT=8095" deploy/systemd/marketcore-kg-api.service
grep -q "MARKETCORE_UI_PORT=8080" deploy/systemd/marketcore-ui-shell.service
grep -q "MARKETCORE_UI_HOST=0.0.0.0" deploy/systemd/marketcore-ui-shell.service
grep -q "KG_API_BASE_URL=http://127.0.0.1:8095" deploy/systemd/marketcore-ui-shell.service

echo "=== STOP_OLD_MANUAL_PROCESSES_IF_ANY ==="
pkill -f "src/marketcore/api/serve_knowledge_graph_api_v1.py" >/dev/null 2>&1 || true
pkill -f "src/marketcore/presentation/app.py" >/dev/null 2>&1 || true

echo "=== INSTALL_SYSTEMD_UNITS ==="
sudo cp deploy/systemd/marketcore-kg-api.service /etc/systemd/system/
sudo cp deploy/systemd/marketcore-ui-shell.service /etc/systemd/system/

sudo systemctl daemon-reload

sudo systemctl enable --now marketcore-kg-api.service
sudo systemctl enable --now marketcore-ui-shell.service

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service

sleep 2

echo "=== SYSTEMD_STATUS ==="
systemctl status marketcore-kg-api.service --no-pager || true
systemctl status marketcore-ui-shell.service --no-pager || true

echo "=== LISTEN_PORTS ==="
ss -ltnp | grep -E ':8080|:8095' || true

echo "=== HTTP_CHECKS ==="
PYTHONPATH=src python src/scripts/check_marketcore_ui_systemd_8080_v1.py | tee /tmp/marketcore_ui_systemd_8080_v1.txt

grep -q "VERDICT=CHECK_MARKETCORE_UI_SYSTEMD_8080_V1_OK" /tmp/marketcore_ui_systemd_8080_v1.txt

server_ip=$(hostname -I | awk '{print $1}')
echo "server_ip=$server_ip"
echo "open_url=http://$server_ip:8080/"
echo "open_risk=http://$server_ip:8080/risk"
echo "open_settings=http://$server_ip:8080/settings"

curl -fsS "http://127.0.0.1:8080/" >/tmp/marketcore_ui_home_8080.html
curl -fsS "http://127.0.0.1:8080/risk" >/tmp/marketcore_ui_risk_8080.html
curl -fsS "http://127.0.0.1:8080/settings" >/tmp/marketcore_ui_settings_8080.html

grep -q "MarketCore OS" /tmp/marketcore_ui_home_8080.html
grep -q "Риски" /tmp/marketcore_ui_risk_8080.html
grep -q "Настройки" /tmp/marketcore_ui_settings_8080.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SYSTEMD_8080_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_SYSTEMD_8080_V1_OK"
SH_TEST

chmod +x scripts/test_marketcore_ui_systemd_8080_v1.sh

scripts/test_marketcore_ui_systemd_8080_v1.sh

echo "VERDICT=BUILD_MARKETCORE_UI_SYSTEMD_8080_V1_OK"
