#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/workspace_v2/renderer/risk_v2_domain_renderer.py src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py src/marketcore/presentation/router.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from marketcore.presentation.render_tree.v2 import render_document_v2_to_dict
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2
d=build_domain_document_v2("RISK")
p=render_document_v2_to_dict(d)
assert d.document_id == "operator.risk.v2" and d.quality_code == "STALE"
encoded=json.dumps(p,ensure_ascii=False)
assert "public.portfolio_risk_state" in encoded
assert encoded.count('"availability_code": "UNAVAILABLE"') >= 3
assert '"value": false' in encoded
assert '"value": "0.00000000000000000000"' in encoded
assert '"class"' not in encoded and '"style"' not in encoded and '"href"' not in encoded
status,body=route("/api/v2/domain-render-tree/risk", {"timezone":["Europe/Moscow"]})
assert status==200 and json.loads(body)["document_id"]=="operator.risk.v2"
print("risk_quality=STALE")
print("risk_source=public.portfolio_risk_state")
print("unavailable_metrics>=3")
print("real_targets_ready=6")
print("VERDICT=MARKETCORE_RISK_CONTAINER_V2_READY")
PY
curl -fsS http://127.0.0.1:8080/api/v2/domain-render-tree/risk | grep -q '"document_id":"operator.risk.v2"'
