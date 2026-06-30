#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_CALIBRATION_AUDIT_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
WITH recent AS (
    SELECT
        symbol,
        block_type,
        block_reason,
        price::numeric AS price,
        atr::numeric AS atr,
        atr_pct::numeric AS atr_pct,
        threshold::numeric AS threshold,
        compression_ratio::numeric AS compression_ratio,
        created_at
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
      AND symbol='BRN6@RTSX'
),
stats AS (
    SELECT
        count(*) AS blocks,
        min(atr_pct) AS min_atr_pct,
        avg(atr_pct) AS avg_atr_pct,
        max(atr_pct) AS max_atr_pct,
        min(threshold) AS min_threshold,
        avg(threshold) AS avg_threshold,
        max(threshold) AS max_threshold,
        min(compression_ratio) AS min_compression_ratio,
        avg(compression_ratio) AS avg_compression_ratio,
        max(compression_ratio) AS max_compression_ratio
    FROM recent
)
SELECT 'br_blocks_2h=' || blocks FROM stats;

WITH x AS (
    SELECT block_type, block_reason, count(*) AS cnt
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
      AND symbol='BRN6@RTSX'
    GROUP BY block_type, block_reason
)
SELECT 'block=' || block_type || '|' || block_reason || '|count=' || cnt
FROM x
ORDER BY cnt DESC, block_type;

WITH stats AS (
    SELECT
        min(atr_pct::numeric) AS min_atr_pct,
        avg(atr_pct::numeric) AS avg_atr_pct,
        max(atr_pct::numeric) AS max_atr_pct,
        avg(threshold::numeric) AS avg_threshold,
        avg(compression_ratio::numeric) AS avg_compression_ratio
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
      AND symbol='BRN6@RTSX'
)
SELECT
'atr_pct=' ||
round(min_atr_pct,6) || '|' ||
round(avg_atr_pct,6) || '|' ||
round(max_atr_pct,6) ||
' threshold_avg=' || round(avg_threshold,6) ||
' compression_ratio_avg=' || round(avg_compression_ratio,6)
FROM stats;

WITH recent AS (
    SELECT atr_pct::numeric AS atr_pct
    FROM public.runtime_guard_pre_signal_block_audit_v1
    WHERE created_at > now() - interval '2 hours'
      AND symbol='BRN6@RTSX'
),
calc AS (
    SELECT
        count(*) AS total,
        sum(CASE WHEN atr_pct >= 0.0003 THEN 1 ELSE 0 END) AS pass_0003,
        sum(CASE WHEN atr_pct >= 0.0004 THEN 1 ELSE 0 END) AS pass_0004,
        sum(CASE WHEN atr_pct >= 0.0005 THEN 1 ELSE 0 END) AS pass_0005,
        sum(CASE WHEN atr_pct >= 0.0007 THEN 1 ELSE 0 END) AS pass_0007,
        sum(CASE WHEN atr_pct >= 0.0010 THEN 1 ELSE 0 END) AS pass_0010
    FROM recent
)
SELECT
'threshold_sensitivity=' ||
'total=' || total ||
'|pass_0003=' || pass_0003 ||
'|pass_0004=' || pass_0004 ||
'|pass_0005=' || pass_0005 ||
'|pass_0007=' || pass_0007 ||
'|pass_0010=' || pass_0010
FROM calc;

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=BR_VOLATILITY_GATE_CALIBRATION_AUDIT_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_CALIBRATION_AUDIT_V1_OK"
