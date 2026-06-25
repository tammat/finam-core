#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_PLAN_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
WITH recent AS (
    SELECT
        symbol,
        strategy,
        timeframe,
        block_type,
        block_reason,
        atr_pct::numeric AS atr_pct,
        threshold::numeric AS current_threshold,
        0.0004::numeric AS shadow_threshold,
        compression_ratio::numeric AS compression_ratio,
        regime,
        trend,
        volatility
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
      AND symbol='BRN6@RTSX'
),
plan AS (
    SELECT
        count(*) AS observations,
        avg(atr_pct) AS avg_atr_pct,
        avg(current_threshold) AS avg_current_threshold,
        avg(shadow_threshold) AS avg_shadow_threshold,
        sum(
            CASE
                WHEN atr_pct >= shadow_threshold THEN 1
                ELSE 0
            END
        ) AS shadow_allow,
        sum(
            CASE
                WHEN atr_pct < shadow_threshold THEN 1
                ELSE 0
            END
        ) AS shadow_block
    FROM recent
)
SELECT 'observations=' || observations FROM plan
UNION ALL
SELECT 'avg_atr_pct=' || round(avg_atr_pct,6) FROM plan
UNION ALL
SELECT 'current_threshold=' || round(avg_current_threshold,6) FROM plan
UNION ALL
SELECT 'shadow_threshold=' || round(avg_shadow_threshold,6) FROM plan
UNION ALL
SELECT 'shadow_allow=' || shadow_allow FROM plan
UNION ALL
SELECT 'shadow_block=' || shadow_block FROM plan;

SELECT 'algorithm=current_decision=BLOCK_FROM_RUNTIME';

SELECT 'algorithm=shadow_decision=CASE WHEN atr_pct>=0.0004 THEN ALLOW ELSE BLOCK END';

SELECT 'algorithm=store_only_if_current_decision_is_BLOCK';

SELECT 'planned_table=research.br_volatility_gate_shadow_observation_v1';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'micro_live_allowed=0';

SELECT 'VERDICT=BR_VOLATILITY_GATE_SHADOW_PLAN_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_PLAN_V1_OK"
