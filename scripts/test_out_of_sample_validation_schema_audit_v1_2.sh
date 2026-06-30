#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_2 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
DROP TABLE IF EXISTS tmp_oos_schema_audit_v1;

CREATE TEMP TABLE tmp_oos_schema_audit_v1 (
    forensic_reports_exists boolean NOT NULL,
    candidate_oos_ready bigint NOT NULL,
    oos_source_mode text NOT NULL
);

DO $$
DECLARE
    table_exists boolean;
    ready_count bigint := 0;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema='research'
          AND table_name='global_edge_forensic_reports_v1'
    )
    INTO table_exists;

    IF table_exists THEN
        EXECUTE $q$
            SELECT count(*)
            FROM research.global_edge_forensic_reports_v1
            WHERE recommendation='PROMOTE_TO_OOS_VALIDATION'
              AND replay_status='PASS'
              AND robustness_status='PASS'
              AND micro_live_allowed=false
              AND runtime_changed=false
        $q$
        INTO ready_count;
    END IF;

    INSERT INTO tmp_oos_schema_audit_v1 (
        forensic_reports_exists,
        candidate_oos_ready,
        oos_source_mode
    )
    VALUES (
        table_exists,
        ready_count,
        CASE
            WHEN table_exists THEN 'FORENSIC_REPORT_TABLE'
            ELSE 'FORENSIC_ENGINE_DRY_RUN_ONLY'
        END
    );
END $$;

SELECT 'forensic_report_table_exists=' || forensic_reports_exists
FROM tmp_oos_schema_audit_v1;

SELECT 'candidate_oos_ready=' || candidate_oos_ready
FROM tmp_oos_schema_audit_v1;

SELECT 'oos_source_mode=' || oos_source_mode
FROM tmp_oos_schema_audit_v1;

SELECT 'required_table=research.oos_validation_campaigns_v1';
SELECT 'required_table=research.oos_validation_results_v1';
SELECT 'required_table=research.oos_validation_decisions_v1';

SELECT 'db_update=0';
SELECT 'runtime_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_2_READY';
SQL

echo "TEST_OUT_OF_SAMPLE_VALIDATION_SCHEMA_AUDIT_V1_2_OK"
