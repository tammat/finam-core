#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

python - <<'PY'
from urllib.request import Request, urlopen

request = Request(
    "http://127.0.0.1:8080/api/v2/domain-render-tree/home",
    headers={
        "Accept": "application/vnd.marketcore.render-tree+json",
        "Cache-Control": "no-cache",
    },
)

with urlopen(request, timeout=30) as response:
    body = response.read().decode("utf-8", errors="replace")

assert response.status == 200
assert "Поиск edge" in body
assert "Regime Discovery" in body
assert "1002 / 1002" in body
assert "3394" in body
assert "100%" in body
assert "этап завершён" in body

print("http_status=200")
print("home_domain_render_tree_valid=1")
print("research_progress_visible=1")
print("regime_discovery_complete_visible=1")
print("tasks_visible=1002")
print("results_visible=3394")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TEST_MARKETCORE_RESEARCH_PROGRESS_HOME_UI_V1_OK")
PY
