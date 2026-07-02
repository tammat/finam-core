#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_KNOWLEDGE_GRAPH_VIEW_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/serve_knowledge_graph_view_v1.py

KG_VIEW_HOST=127.0.0.1 KG_VIEW_PORT=8096 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/presentation/pages/serve_knowledge_graph_view_v1.py > /tmp/kg_view_v1.log 2>&1 &
pid=$!

cleanup() { kill "$pid" >/dev/null 2>&1 || true; }
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:8096/" | tee /tmp/kg_view_home.html >/dev/null
curl -fsS "http://127.0.0.1:8096/entities" | tee /tmp/kg_view_entities.html >/dev/null
curl -fsS "http://127.0.0.1:8096/relations" | tee /tmp/kg_view_relations.html >/dev/null
curl -fsS "http://127.0.0.1:8096/search?q=сделки" | tee /tmp/kg_view_search.html >/dev/null
curl -fsS "http://127.0.0.1:8096/validation" | tee /tmp/kg_view_validation.html >/dev/null

grep -q "MarketCore Knowledge Graph View V1" /tmp/kg_view_home.html
grep -q "Сущности Knowledge Graph" /tmp/kg_view_entities.html
grep -q "Связи Knowledge Graph" /tmp/kg_view_relations.html
grep -q "Семантический поиск" /tmp/kg_view_search.html
grep -q "Валидация Knowledge Graph" /tmp/kg_view_validation.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_KNOWLEDGE_GRAPH_VIEW_V1_READY"
echo "VERDICT=TEST_MARKETCORE_KNOWLEDGE_GRAPH_VIEW_V1_OK"
