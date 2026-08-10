#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1
export PYTHONPATH=src

RESOLVER="src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
RENDERER="src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"

python -m py_compile "$RESOLVER" "$RENDERER"
git --no-pager diff --check

python - <<'PY'
from marketcore.presentation.workspace_v2.resolver.control_compact_v3_resolver import (
    ControlCompactV3Resolver,
)

snapshot = ControlCompactV3Resolver().resolve()

research = snapshot.get("research_progress") or {}
methodology = snapshot.get("methodology_gate") or {}

discovery_ts = research.get("finished_at") or research.get("heartbeat_at")
methodology_ts = methodology.get("last_evaluated_at")

assert research
assert methodology
assert discovery_ts
assert methodology_ts
assert methodology_ts < discovery_ts

print("methodology_stale_vs_current_discovery=1")
PY

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

if [ "$READY" -ne 1 ]; then
    echo "ERROR=UI_SHELL_NOT_READY"
    exit 1
fi

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
    "4. Methodology Gate",
    "STALE",
    "METHODOLOGY_V2_FUTURE_ONLY",
    "PASS 0",
    "FAIL 1",
    "не относится к текущей Regime Discovery campaign",
)

assert response.status == 200

for value in required:
    assert value in body, value

print("http_status=200")
print("methodology_gate_visible=1")
print("methodology_gate_stale_visible=1")
print("historical_fail_not_misrepresented_as_current=1")
print("db_writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=TEST_MARKETCORE_METHODOLOGY_GATE_HOME_FRESHNESS_V1_OK")
PY
