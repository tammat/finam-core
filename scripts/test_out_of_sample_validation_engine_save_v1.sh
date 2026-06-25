#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OUT_OF_SAMPLE_VALIDATION_ENGINE_SAVE_V1 ==="

src/scripts/research/build_out_of_sample_validation_engine_v1.py \
  --candidate-id MSC-000001 \
  --save \
  | tee /tmp/oos_validation_engine_save_v1.out

grep -q "OUT_OF_SAMPLE_VALIDATION_ENGINE_V1" /tmp/oos_validation_engine_save_v1.out
grep -q "mode=save" /tmp/oos_validation_engine_save_v1.out
grep -q "candidate_id=MSC-000001" /tmp/oos_validation_engine_save_v1.out
grep -q "status=OOS_PASS" /tmp/oos_validation_engine_save_v1.out
grep -q "decision=PASS_TO_SHADOW" /tmp/oos_validation_engine_save_v1.out
grep -q "runtime_changed=0" /tmp/oos_validation_engine_save_v1.out
grep -q "micro_live_allowed=0" /tmp/oos_validation_engine_save_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'campaigns=' || count(*)
FROM research.oos_validation_campaigns_v1
WHERE candidate_id='MSC-000001';

SELECT 'results=' || count(*)
FROM research.oos_validation_results_v1 r
JOIN research.oos_validation_campaigns_v1 c ON c.campaign_id=r.campaign_id
WHERE c.candidate_id='MSC-000001';

SELECT 'decisions=' || count(*)
FROM research.oos_validation_decisions_v1 d
JOIN research.oos_validation_campaigns_v1 c ON c.campaign_id=d.campaign_id
WHERE c.candidate_id='MSC-000001';

SELECT 'latest_decision=' ||
       d.decision || '|' ||
       d.decision_reason || '|' ||
       d.runtime_changed || '|' ||
       d.micro_live_allowed
FROM research.oos_validation_decisions_v1 d
JOIN research.oos_validation_campaigns_v1 c ON c.campaign_id=d.campaign_id
WHERE c.candidate_id='MSC-000001'
ORDER BY d.created_at DESC
LIMIT 1;

SELECT 'VERDICT=OUT_OF_SAMPLE_VALIDATION_ENGINE_SAVE_V1_READY';
SQL

echo "TEST_OUT_OF_SAMPLE_VALIDATION_ENGINE_SAVE_V1_OK"
