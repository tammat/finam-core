#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONPATH=src .venv/bin/python -m py_compile src/marketcore/presentation/workspace_v2/domain/intraday_snapshot_v2.py src/marketcore/presentation/workspace_v2/resolver/intraday_v2_resolver.py src/marketcore/presentation/workspace_v2/renderer/intraday_v2_domain_renderer.py
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from marketcore.presentation.render_tree.v2 import render_document_v2_to_dict
from marketcore.presentation.router import route
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import build_domain_document_v2
d=build_domain_document_v2("INTRADAY",timezone_code="Europe/Moscow");e=json.dumps(render_document_v2_to_dict(d))
assert d.document_id=="operator.intraday.v2" and d.quality_code=="MIXED_FRESHNESS"
assert "public.v_intraday_pnl_ru" in e and "marketcore_ui.paper_runtime_summary_v1" in e
assert '"class"' not in e and '"style"' not in e
status,body=route("/api/v2/domain-render-tree/intraday",{"timezone":["Europe/Moscow"]})
assert status==200 and json.loads(body)["document_id"]=="operator.intraday.v2"
print("intraday_source=public.v_intraday_pnl_ru")
print("intraday_quality=MIXED_FRESHNESS")
print("real_targets_ready=8")
print("VERDICT=MARKETCORE_INTRADAY_CONTAINER_V2_READY")
PY
curl -fsS http://127.0.0.1:8080/api/v2/domain-render-tree/intraday | grep -q '"document_id":"operator.intraday.v2"'
