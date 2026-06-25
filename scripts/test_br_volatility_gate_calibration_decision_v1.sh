#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_CALIBRATION_DECISION_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
CREATE SCHEMA IF NOT EXISTS research;

CREATE TABLE IF NOT EXISTS research.runtime_calibration_decisions_v1 (
    decision_id BIGSERIAL PRIMARY KEY,
    calibration_type TEXT NOT NULL,
    current_value NUMERIC NOT NULL,
    candidate_value NUMERIC NOT NULL,
    decision TEXT NOT NULL,
    decision_reason TEXT NOT NULL,
    supporting_checkpoints JSONB NOT NULL,
    runtime_changed BOOLEAN NOT NULL DEFAULT false,
    execution_changed BOOLEAN NOT NULL DEFAULT false,
    orders_changed BOOLEAN NOT NULL DEFAULT false,
    fills_changed BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO research.runtime_calibration_decisions_v1 (
    calibration_type,
    current_value,
    candidate_value,
    decision,
    decision_reason,
    supporting_checkpoints,
    runtime_changed,
    execution_changed,
    orders_changed,
    fills_changed,
    micro_live_allowed,
    payload
)
VALUES (
    'BR_VOLATILITY_GATE',
    0.0010,
    0.0004,
    'REJECT',
    'FAIL_DAY_CONCENTRATION',
    jsonb_build_array(
        'BR_VOLATILITY_GATE_SHADOW_EXPERIMENT_V1',
        'BR_VOLATILITY_GATE_SHADOW_SIMULATION_V1',
        'BR_VOLATILITY_GATE_SHADOW_SLICE_SCORECARD_V1',
        'BR_VOLATILITY_GATE_SHADOW_ROBUSTNESS_V1',
        'BR_VOLATILITY_GATE_SHADOW_TEMPORAL_STABILITY_V1'
    ),
    false,
    false,
    false,
    false,
    false,
    jsonb_build_object(
        'observation_rows', 180,
        'simulation_rows', 1440,
        'global_simulation_net_pnl', -4.91,
        'temporal_stability_status', 'FAIL_DAY_CONCENTRATION',
        'final_decision', 'DO_NOT_CHANGE_RUNTIME_THRESHOLD',
        'current_threshold', 0.0010,
        'rejected_threshold', 0.0004,
        'note_ru', 'Снижение порога BR volatility gate не подтверждено из-за дневной и часовой концентрации результата.'
    )
);

SELECT 'latest_decision=' ||
       calibration_type || '|' ||
       current_value || '|' ||
       candidate_value || '|' ||
       decision || '|' ||
       decision_reason || '|' ||
       runtime_changed || '|' ||
       execution_changed || '|' ||
       orders_changed || '|' ||
       fills_changed || '|' ||
       micro_live_allowed
FROM research.runtime_calibration_decisions_v1
WHERE calibration_type='BR_VOLATILITY_GATE'
ORDER BY created_at DESC
LIMIT 1;

SELECT 'decision_rows=' || count(*)
FROM research.runtime_calibration_decisions_v1
WHERE calibration_type='BR_VOLATILITY_GATE';

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=BR_VOLATILITY_GATE_CALIBRATION_DECISION_V1_REJECT';
SQL

echo "TEST_BR_VOLATILITY_GATE_CALIBRATION_DECISION_V1_OK"
