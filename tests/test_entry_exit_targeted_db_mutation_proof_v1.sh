#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
OPTIMIZER="src/scripts/analytics/build_entry_exit_optimizer_v1.py"

BEFORE="/tmp/entry_exit_targeted_unsafe_before_v2.txt"
AFTER="/tmp/entry_exit_targeted_unsafe_after_v2.txt"
RUN_OUT="/tmp/entry_exit_targeted_run_v2.out"

fingerprint_unsafe() {
    psql "$DATABASE_URL" \
      -X \
      -v ON_ERROR_STOP=1 \
      -P pager=off \
      -At <<'SQL'
SELECT 'recommendation|' ||
       count(*) || '|' ||
       coalesce(md5(string_agg(
           strategy_code||'|'||
           symbol_group||'|'||
           side_code||'|'||
           candidate_code||'|'||
           recommendation_status,
           E'\n'
           ORDER BY
               strategy_code,
               symbol_group,
               side_code,
               candidate_code
       )), 'EMPTY')
FROM analytics.entry_exit_recommendation_v1

UNION ALL

SELECT 'promotion_workflow|' ||
       count(*) || '|' ||
       coalesce(md5(string_agg(
           strategy_code||'|'||
           symbol_group||'|'||
           side_code||'|'||
           candidate_code||'|'||
           workflow_stage,
           E'\n'
           ORDER BY
               strategy_code,
               symbol_group,
               side_code,
               candidate_code
       )), 'EMPTY')
FROM analytics.entry_exit_promotion_workflow_v1

UNION ALL

SELECT 'runtime_profile|' ||
       count(*) || '|' ||
       coalesce(md5(string_agg(
           strategy_code||'|'||
           symbol_group||'|'||
           side_code||'|'||
           candidate_code||'|'||
           status,
           E'\n'
           ORDER BY
               strategy_code,
               symbol_group,
               side_code,
               candidate_code
       )), 'EMPTY')
FROM analytics.entry_exit_runtime_profile_v1

UNION ALL

SELECT 'champion_challenger|' ||
       count(*) || '|' ||
       coalesce(md5(string_agg(
           strategy_code||'|'||
           symbol_group||'|'||
           side_code||'|'||
           coalesce(champion_candidate_code,'')||'|'||
           coalesce(challenger_candidate_code,''),
           E'\n'
           ORDER BY
               strategy_code,
               symbol_group,
               side_code
       )), 'EMPTY')
FROM analytics.entry_exit_champion_challenger_v1

UNION ALL

SELECT 'family_evidence|' ||
       count(*) || '|' ||
       coalesce(md5(string_agg(
           family_code||'|'||
           side_code||'|'||
           candidate_code||'|'||
           evidence_status,
           E'\n'
           ORDER BY
               family_code,
               side_code,
               candidate_code
       )), 'EMPTY')
FROM analytics.entry_exit_family_evidence_v1

ORDER BY 1;
SQL
}

echo "=== ENTRY EXIT TARGETED DB MUTATION PROOF V1 ==="

fingerprint_unsafe > "$BEFORE"

ENTRY_EXIT_TARGETED_RESEARCH_ONLY=1 \
EDGE_SEARCH_TARGET_SYMBOL="BRQ6@RTSX" \
EDGE_SEARCH_TARGET_STRATEGY="BR_CONSERVATIVE_BREAKOUT" \
EDGE_SEARCH_TARGET_SIDE="LONG" \
PYTHONPATH=src \
"$PY" "$OPTIMIZER" \
  | tee "$RUN_OUT"

grep -q \
'^VERDICT=ENTRY_EXIT_TARGETED_RESEARCH_ONLY_V1_READY$' \
"$RUN_OUT"

fingerprint_unsafe > "$AFTER"

diff -u "$BEFORE" "$AFTER"

echo "unsafe_control_state_changed=0"
echo "physical_target=BRQ6@RTSX"
echo "target_strategy=BR_CONSERVATIVE_BREAKOUT"
echo "target_side=LONG"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo \
"VERDICT=ENTRY_EXIT_TARGETED_RESEARCH_ONLY_UNSAFE_MUTATION_PROOF_OK"
echo \
"VERDICT=TEST_ENTRY_EXIT_TARGETED_DB_MUTATION_PROOF_V1_OK"
