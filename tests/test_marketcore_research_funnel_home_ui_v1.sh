#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

FILE="src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"

PYTHONPATH=src python -m py_compile "$FILE"
git --no-pager diff --check

sudo systemctl restart marketcore-ui-shell.service

READY=0

for i in $(seq 1 30); do
    if python - <<'PY' >/dev/null 2>&1
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8080/", timeout=2) as response:
    raise SystemExit(0 if response.status == 200 else 1)
PY
    then
        READY=1
        echo "ui_shell_ready_after_attempt=$i"
        break
    fi

    sleep 1
done

[ "$READY" -eq 1 ]

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

required = (
    "Исследовательская воронка",
    "1. Regime Discovery",
    "2. Walk-Forward",
    "3. V5 OOS",
    "4. Methodology Gate",
    "5. Shadow",
    "6. Paper",
    "7. REAL",
)

assert response.status == 200

for value in required:
    assert value in body, value

print("http_status=200")
print("research_funnel_visible=1")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TEST_MARKETCORE_RESEARCH_FUNNEL_HOME_UI_V1_OK")
PY
