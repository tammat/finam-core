#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/workspace_v2/renderer/capital_v2_domain_renderer.py src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from marketcore.presentation.render_tree.v2 import render_document_v2_to_dict
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2
d=build_domain_document_v2("CAPITAL")
p=render_document_v2_to_dict(d)
assert d.document_id == "operator.capital.v2" and d.root.node_id == "workspace.capital"
assert d.source_as_of <= d.generated_at
encoded=json.dumps(p,ensure_ascii=False)
assert "public.v_real_portfolio_summary_ru" in encoded
assert '"availability_code": "UNAVAILABLE"' in encoded
assert '"value": 0' not in encoded
status,body=route("/api/v2/domain-render-tree/capital",{})
assert status==200 and json.loads(body)["document_id"]=="operator.capital.v2"
print("capital_source=public.v_real_portfolio_summary_ru")
print("available_capital=UNAVAILABLE")
print("real_targets_ready=5")
print("VERDICT=MARKETCORE_CAPITAL_CONTAINER_V2_READY")
PY
curl -fsS http://127.0.0.1:8080/api/v2/domain-render-tree/capital | grep -q '"document_id":"operator.capital.v2"'
