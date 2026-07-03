#!/usr/bin/env bash
set -euo pipefail

echo "=== PATCH_EDGE_LEGACY_RESEARCH_CANDIDATES_REMOVE_V1 ==="

python - <<'PY'
from pathlib import Path

# 1. API: старый source убираем из пользовательских endpoint-ов.
p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

s = s.replace(
    "marketcore_ui.paper_edge_research_candidates_v1",
    "marketcore_ui.market_universe_research_queue_v1"
)

s = s.replace(
    "candidate_rank",
    "queue_rank"
)

s = s.replace(
    '"source": "marketcore_ui.market_universe_research_queue_v1"',
    '"source": "marketcore_ui.market_universe_research_queue_v1"'
)

p.write_text(s)

# 2. UI page: только текст источника, чтобы не показывать legacy.
p = Path("src/marketcore/presentation/pages/paper_edge_discovery.py")
s = p.read_text()

s = s.replace(
    "marketcore_ui.paper_edge_research_candidates_v1 через Knowledge Graph API",
    "marketcore_ui.market_universe_research_queue_v1 через Knowledge Graph API"
)

s = s.replace(
    "marketcore_ui.paper_edge_research_candidates_v1",
    "marketcore_ui.market_universe_research_queue_v1"
)

p.write_text(s)

# 3. Validation queue builder: переводим источник на Research Queue.
p = Path("src/scripts/build_edge_validation_queue_v1.py")
s = p.read_text()

s = s.replace(
    "FROM marketcore_ui.paper_edge_research_candidates_v1",
    "FROM marketcore_ui.market_universe_research_queue_v1"
)

s = s.replace(
    "candidate_rank",
    "queue_rank"
)

s = s.replace(
    "strategy",
    "recommended_strategy_family AS strategy"
)

s = s.replace(
    "side",
    "''::text AS side"
)

p.write_text(s)
PY

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/scripts/build_edge_validation_queue_v1.py

echo "VERDICT=PATCH_EDGE_LEGACY_RESEARCH_CANDIDATES_REMOVE_V1_READY"
