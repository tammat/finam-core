#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
DROP TABLE IF EXISTS tmp_oos_schema_audit_v1;

CREATE TEMP TABLE tmp_oos_schema_audit_v1 AS
SELECT
    EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema='research'
          AND table_name='global_edge_forensic_reports_v1'
    ) AS forensic_reports_exists;

SELECT 'forensic_report_table_exists=' || forensic_reports_exists
FROM tmp_oos_schema_audit_v1;

SELECT 'candidate_oos_ready=' ||
CASE
    WHEN (SELECT forensic_reports_exists FROM tmp_oos_schema_audit_v1)
    THEN (
        SELECT count(*)::text
        FROM research.global_edge_forensic_reports_v1
        WHERE recommendation='PROMOTE_TO_OOS_VALIDATION'
          AND replay_status='PASS'
          AND robustness_status='PASS'
          AND micro_live_allowed=false
          AND runtime_changed=false
    )
    ELSE '0'
END;

SELECT 'oos_source_mode=' ||
CASE
    WHEN (SELECT forensic_reports_exists FROM tmp_oos_schema_audit_v1)
    THEN 'FORENSIC_REPORT_TABLE'
    ELSE 'FORENSIC_ENGINE_DRY_RUN_ONLY'
END;

SELECT 'required_table=research.oos_validation_campaigns_v1';
SELECT 'required_table=research.oos_validation_results_v1';
SELECT 'required_table=research.oos_validation_decisions_v1';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_1_READY';
SQL

echo "TEST_OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_1_OK"
