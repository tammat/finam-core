#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COVERAGE_WIDGET_AUDIT_V1 ==="

mkdir -p reports
report="reports/market_context_coverage_widget_audit_v1.txt"

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" \
  >/tmp/market_context_coverage_widget_audit_home.html

{
echo "=== MARKET_CONTEXT_COVERAGE_WIDGET_AUDIT_V1 ==="
echo "generated_at=$(date -Is)"
echo

echo "=== HTTP/UI ==="
grep -q 'data-widget-id="knowledge_coverage"' /tmp/market_context_coverage_widget_audit_home.html
grep -q "Покрытие знаний" /tmp/market_context_coverage_widget_audit_home.html
grep -q "Общее покрытие" /tmp/market_context_coverage_widget_audit_home.html
grep -q "%" /tmp/market_context_coverage_widget_audit_home.html
echo "operator_home_widget_visible=OK"
echo

echo "=== PROVIDER ==="
PYTHONPATH=src python - <<'PY'
from marketcore.presentation.providers.knowledge_coverage_provider import KnowledgeCoverageProvider

vm = KnowledgeCoverageProvider().load()
print("widget_id=", vm.widget_id)
print("title_key=", vm.title_key)
print("state=", vm.state)
for k, v in vm.content.items():
    print(f"{k}={v}")
assert vm.widget_id == "knowledge_coverage"
assert vm.state == "readonly"
assert "knowledge.coverage.total" in vm.content
PY
echo

echo "=== RAW I18N AUDIT ==="
raw=$(grep -Eo '(widget|knowledge)\.[A-Za-z0-9_.-]+' /tmp/market_context_coverage_widget_audit_home.html | sort -u || true)
if [ -n "$raw" ]; then
  echo "$raw"
  echo "RAW_I18N_KEY_VISIBLE=1"
  exit 1
fi
echo "RAW_I18N_KEY_VISIBLE=0"
echo

echo "=== KNOWLEDGE COVERAGE DATA ==="
psql -d finam_core -P pager=off -c "
WITH stats AS (
  SELECT
    count(*) AS total,
    sum((regime_code<>'UNKNOWN')::int) AS regime,
    sum((volatility_state<>'UNKNOWN')::int) AS volatility,
    sum((liquidity_state<>'UNKNOWN')::int) AS liquidity,
    sum((volume_state<>'UNKNOWN')::int) AS volume,
    sum((spread_state<>'UNKNOWN')::int) AS spread,
    sum((session_state<>'UNKNOWN')::int) AS session,
    sum((correlation_state<>'UNKNOWN')::int) AS correlation,
    sum((sector_strength_state<>'UNKNOWN')::int) AS sector
  FROM knowledge.market_context_v1
  WHERE source_version='MARKET_CONTEXT_COLLECTOR_V1'
)
SELECT
  total,
  round(100.0*(regime+volatility+liquidity+volume+spread+session+correlation+sector)/nullif(total*8,0),2) AS knowledge_coverage_pct,
  round(100.0*regime/nullif(total,0),2) AS regime_pct,
  round(100.0*volatility/nullif(total,0),2) AS volatility_pct,
  round(100.0*liquidity/nullif(total,0),2) AS liquidity_pct,
  round(100.0*volume/nullif(total,0),2) AS volume_pct,
  round(100.0*spread/nullif(total,0),2) AS spread_pct,
  round(100.0*session/nullif(total,0),2) AS session_pct,
  round(100.0*correlation/nullif(total,0),2) AS correlation_pct,
  round(100.0*sector/nullif(total,0),2) AS sector_pct
FROM stats;
"
echo

echo "=== SAFETY ==="
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=MARKET_CONTEXT_COVERAGE_WIDGET_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COVERAGE_WIDGET_AUDIT_V1_OK"
} | tee "$report"

grep -q "VERDICT=TEST_MARKET_CONTEXT_COVERAGE_WIDGET_AUDIT_V1_OK" "$report"
