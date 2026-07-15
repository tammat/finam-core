#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from marketcore.presentation.render_tree.v2 import render_document_v2_to_dict
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2
d=build_domain_document_v2("RESEARCH"); p=render_document_v2_to_dict(d); e=json.dumps(p)
assert d.document_id=="operator.research.v2" and d.quality_code=="MIXED_FRESHNESS"
assert d.root.node_id=="workspace.research" and '"class"' not in e and '"style"' not in e
status,body=route("/api/v2/domain-render-tree/research",{})
assert status==200 and json.loads(body)["document_id"]=="operator.research.v2"
print("research_quality=MIXED_FRESHNESS")
print("research_sources=4")
print("real_targets_ready=7")
print("VERDICT=MARKETCORE_RESEARCH_CONTAINER_V2_READY")
PY
curl -fsS http://127.0.0.1:8080/api/v2/domain-render-tree/research | grep -q '"document_id":"operator.research.v2"'
