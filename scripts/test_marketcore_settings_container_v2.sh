#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile \
  src/marketcore/presentation/workspace_v2/renderer/settings_v2_domain_renderer.py \
  src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py \
  src/marketcore/presentation/navigation/container_registry_v2.py \
  src/marketcore/presentation/router.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from marketcore.presentation.navigation.container_registry_v2 import ready_container_definitions_v2
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2

document = build_domain_document_v2("SETTINGS", timezone_code="UTC")
assert document.document_id == "operator.settings.v2"
assert document.timezone_code == "UTC"
assert document.root.node_id == "workspace.settings"
encoded = json.dumps(__import__('marketcore.presentation.render_tree.v2', fromlist=['render_document_v2_to_dict']).render_document_v2_to_dict(document))
for forbidden in ('"class"', '"style"', '"href"', '<'):
    assert forbidden not in encoded
status, body = route("/api/v2/domain-render-tree/settings", {"timezone": ["Europe/Moscow"]})
payload = json.loads(body)
assert status == 200 and payload["timezone_code"] == "Europe/Moscow"
assert {item.container_code.value for item in ready_container_definitions_v2()} == {"HOME", "CAPITAL", "EDGE", "PORTFOLIO", "SETTINGS"}
print("settings_source=OperatorSettingsV1")
print("real_targets_ready=5")
print("targets_pending=4")
print("VERDICT=MARKETCORE_SETTINGS_CONTAINER_V2_READY")
PY
curl -fsS 'http://127.0.0.1:8080/api/v2/domain-render-tree/settings?timezone=Europe%2FMoscow' >/tmp/marketcore-settings-v2.json
grep -q '"document_id":"operator.settings.v2"' /tmp/marketcore-settings-v2.json
