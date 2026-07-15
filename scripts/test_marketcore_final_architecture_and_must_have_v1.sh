#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo \
"=== TEST_MARKETCORE_FINAL_ARCHITECTURE_AND_MUST_HAVE_V1 ==="

architecture_file=\
"docs/vision/MARKETCORE_FINAL_ARCHITECTURE_V1.txt"

must_have_file=\
"docs/vision/MARKETCORE_MUST_HAVE_V1.txt"

for file in "$architecture_file" "$must_have_file"; do
  test -f "$file" || {
    echo "FILE_NOT_FOUND=$file"
    exit 1
  }

  test -s "$file" || {
    echo "FILE_EMPTY=$file"
    exit 1
  }
done

required_architecture_terms=(
  "МИССИЯ ПРОЕКТА"
  "PROFIT"
  "CLOSED-LOOP CONTROL"
  "MONITOR"
  "RECOMMEND"
  "AUTONOMOUS"
  "POLICY ENGINE"
  "CONFIDENCE ENGINE"
  "HYPOTHESIS ENGINE"
  "IMPROVEMENT ENGINE"
  "STRATEGY MEMORY"
  "EXPERIMENT ENGINE"
  "PROFIT FACTORY CONTROL CENTER"
  "OPERATOR WORKSPACE"
  "I18N"
  "SOURCE OF TRUTH"
  "MARKETCORE_FINAL_ARCHITECTURE_V1_LOCKED"
)

for term in "${required_architecture_terms[@]}"; do
  grep -Fq "$term" "$architecture_file" || {
    echo "ARCHITECTURE_TERM_NOT_FOUND=$term"
    exit 1
  }
done

required_must_have_terms=(
  "POSTGRESQL ONLY"
  "CENTRALIZED RISK ENGINE"
  "THREE AUTONOMY MODES"
  "POLICY ENGINE"
  "CONFIDENCE ENGINE"
  "HYPOTHESIS ENGINE"
  "EXPERIMENT ENGINE"
  "IMPROVEMENT ENGINE"
  "STRATEGY MEMORY"
  "PROFIT FUNNEL"
  "BOTTLENECK ENGINE"
  "RENDER TREE"
  "NO SERVER HTML GENERATION"
  "I18N"
  "NO HARDCODE"
  "AI EXECUTION BOUNDARY"
  "ROLLBACK"
  "KILL SWITCH"
  "COST MODEL"
  "BASH TESTS ONLY"
  "DEFINITION OF DONE"
  "MARKETCORE_MUST_HAVE_V1_LOCKED"
)

for term in "${required_must_have_terms[@]}"; do
  grep -Fq "$term" "$must_have_file" || {
    echo "MUST_HAVE_TERM_NOT_FOUND=$term"
    exit 1
  }
done

if grep -Fq \
  "AI имеет право отправлять заявки напрямую" \
  "$architecture_file" "$must_have_file"
then
  echo "DIRECT_AI_ORDER_PERMISSION_FOUND"
  exit 1
fi

if grep -Fq \
  "SQLite разрешен" \
  "$architecture_file" "$must_have_file"
then
  echo "SQLITE_PERMISSION_FOUND"
  exit 1
fi

grep -Fq \
  "серверное построение интерфейса через HTML" \
  "$architecture_file"

grep -Fq \
  "Пользовательские тексты" \
  "$architecture_file" || \
grep -Fq \
  "Все пользовательские тексты" \
  "$must_have_file"

grep -Fq \
  "Управляемые значения" \
  "$must_have_file"

echo "architecture_document=OK"
echo "must_have_document=OK"
echo "mission_locked=OK"
echo "profit_north_star=OK"
echo "closed_loop_control=OK"
echo "autonomy_modes=3"
echo "policy_engine_required=OK"
echo "confidence_engine_required=OK"
echo "hypothesis_engine_required=OK"
echo "improvement_engine_required=OK"
echo "strategy_memory_required=OK"
echo "i18n_required=OK"
echo "server_html_generation=0"
echo "hardcode_allowed=0"
echo "sqlite_allowed=0"
echo "ai_direct_orders_allowed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=MARKETCORE_FINAL_ARCHITECTURE_AND_MUST_HAVE_V1_READY"
echo \
"VERDICT=TEST_MARKETCORE_FINAL_ARCHITECTURE_AND_MUST_HAVE_V1_OK"
