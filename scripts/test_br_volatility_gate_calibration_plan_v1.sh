#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_CALIBRATION_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
WITH recent AS (
    SELECT
        symbol,
        block_type,
        block_reason,
        atr_pct::numeric AS atr_pct,
        threshold::numeric AS threshold,
        compression_ratio::numeric AS compression_ratio,
        created_at
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
      AND symbol='BRN6@RTSX'
),
plan AS (
    SELECT
        count(*) AS total_blocks,
        sum(CASE WHEN block_type='VOL_LOW_BLOCK' THEN 1 ELSE 0 END) AS vol_low_blocks,
        sum(CASE WHEN block_type='COMPRESSION_WATCH' THEN 1 ELSE 0 END) AS compression_blocks,
        avg(atr_pct) AS avg_atr_pct,
        avg(threshold) AS current_threshold,
        0.0004::numeric AS candidate_threshold,
        sum(CASE WHEN atr_pct >= 0.0004 THEN 1 ELSE 0 END) AS would_pass_candidate_threshold,
        sum(CASE WHEN atr_pct >= 0.0010 THEN 1 ELSE 0 END) AS would_pass_current_threshold
    FROM recent
)
SELECT 'current_threshold=' || round(current_threshold,6) FROM plan
UNION ALL
SELECT 'candidate_threshold=' || candidate_threshold FROM plan
UNION ALL
SELECT 'avg_atr_pct=' || round(avg_atr_pct,6) FROM plan
UNION ALL
SELECT 'total_blocks=' || total_blocks FROM plan
UNION ALL
SELECT 'vol_low_blocks=' || vol_low_blocks FROM plan
UNION ALL
SELECT 'compression_blocks=' || compression_blocks FROM plan
UNION ALL
SELECT 'would_pass_current_threshold=' || would_pass_current_threshold FROM plan
UNION ALL
SELECT 'would_pass_candidate_threshold=' || would_pass_candidate_threshold FROM plan;

SELECT 'planned_action=CREATE_SHADOW_ONLY_BR_VOL_THRESHOLD_OBSERVATION';
SELECT 'planned_threshold=0.0004';
SELECT 'planned_scope=BRN6@RTSX_ONLY';
SELECT 'planned_mode=shadow_observation_only';
SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=BR_VOLATILITY_GATE_CALIBRATION_PLAN_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_CALIBRATION_PLAN_V1_OK"
