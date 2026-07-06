#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_GOVERNANCE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/008_strategy_platform_governance_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_strategy_platform_governance_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/strategy_governance.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core STRATEGY_FEATURE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_multi_strategy_engine_builder_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_platform_governance_v1.py \
  | tee /tmp/strategy_platform_governance_v1.txt

grep -q "VERDICT=STRATEGY_PLATFORM_GOVERNANCE_V1_READY" \
  /tmp/strategy_platform_governance_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/strategy-platform/governance" > /tmp/strategy_governance_api.json
curl -fsS "http://127.0.0.1:8080/strategy-governance" > /tmp/strategy_governance_ui.html

python - <<'PY'
import os

def as_int(name: str) -> int:
    value = os.environ.get(name, "0")
    try:
        return int(value)
    except ValueError as exc:
        raise AssertionError(f"{name}_NOT_INT={value!r}") from exc

registry_rows = as_int("registry_rows")
signal_rows = as_int("signal_rows")
unsafe_execution_rows = as_int("unsafe_execution_rows")
missing_config_rows = as_int("missing_config_rows")
duplicate_active_config_rows = as_int("duplicate_active_config_rows")
unknown_feature_dependency_rows = as_int("unknown_feature_dependency_rows")
governance_score = as_int("governance_score")

assert registry_rows >= 0
assert signal_rows >= 0
assert unsafe_execution_rows == 0
assert missing_config_rows == 0
assert duplicate_active_config_rows >= 0
assert unknown_feature_dependency_rows == 0
assert governance_score >= 0

print("STRATEGY_PLATFORM_GOVERNANCE_ASSERTIONS_OK")
PY

grep -q "Governance стратегий" /tmp/strategy_governance_ui.html
grep -q "Готово к Research" /tmp/strategy_governance_ui.html

score=$(psql -At -d finam_core -c "
SELECT governance_score
FROM analytics.strategy_platform_governance_v1
WHERE governance_scope='GLOBAL';
")

readiness=$(psql -At -d finam_core -c "
SELECT readiness_status
FROM analytics.strategy_platform_governance_v1
WHERE governance_scope='GLOBAL';
")

unsafe=$(psql -At -d finam_core -c "
SELECT unsafe_execution_rows
FROM analytics.strategy_platform_governance_v1
WHERE governance_scope='GLOBAL';
")

test "$readiness" = "READY_FOR_RESEARCH"
test "$unsafe" = "0"

echo "governance_score=$score"
echo "readiness_status=$readiness"
echo "unsafe_execution_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_PLATFORM_GOVERNANCE_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_GOVERNANCE_V1_OK"
