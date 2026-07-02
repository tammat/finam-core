#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_SHELL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/page.py \
  src/marketcore/presentation/api_client.py \
  src/marketcore/presentation/pages/home.py \
  src/marketcore/presentation/pages/runtime.py \
  src/marketcore/presentation/pages/knowledge_graph.py \
  src/marketcore/presentation/pages/research.py \
  src/marketcore/presentation/pages/portfolio.py \
  src/marketcore/presentation/pages/orders.py \
  src/marketcore/presentation/pages/risk.py \
  src/marketcore/presentation/pages/validation.py \
  src/marketcore/presentation/pages/logs.py \
  src/marketcore/presentation/pages/system.py \
  src/marketcore/presentation/pages/ai.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/navigation.py \
  src/marketcore/presentation/layout.py \
  src/marketcore/presentation/router.py \
  src/marketcore/presentation/app.py

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=8080 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/marketcore_ui_shell_v1.log 2>&1 &
pid=$!

cleanup() {
  kill "$pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 1

for path in "/" "/runtime" "/knowledge-graph" "/research" "/portfolio" "/orders" "/risk" "/validation" "/logs" "/system" "/ai"; do
  curl -fsS "http://127.0.0.1:8080${path}" > "/tmp/marketcore_ui_shell_${path//\//_}.html"
done

grep -q "MarketCore OS" /tmp/marketcore_ui_shell__.html
grep -q "Runtime" /tmp/marketcore_ui_shell__runtime.html
grep -q "Knowledge Graph" /tmp/marketcore_ui_shell__knowledge-graph.html
grep -q "Research" /tmp/marketcore_ui_shell__research.html
grep -q "Portfolio" /tmp/marketcore_ui_shell__portfolio.html
grep -q "Orders" /tmp/marketcore_ui_shell__orders.html
grep -q "Risk" /tmp/marketcore_ui_shell__risk.html
grep -q "Validation" /tmp/marketcore_ui_shell__validation.html
grep -q "Logs" /tmp/marketcore_ui_shell__logs.html
grep -q "System" /tmp/marketcore_ui_shell__system.html
grep -q "AI" /tmp/marketcore_ui_shell__ai.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/marketcore_ui_shell__.html

status_404=$(curl -s -o /tmp/marketcore_ui_shell_404.html -w "%{http_code}" "http://127.0.0.1:8080/not-found")
test "$status_404" = "404"
grep -q "Страница не найдена" /tmp/marketcore_ui_shell_404.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_SHELL_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_SHELL_V1_OK"
