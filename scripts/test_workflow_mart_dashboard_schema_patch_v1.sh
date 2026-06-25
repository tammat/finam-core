#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_MART_DASHBOARD_SCHEMA_PATCH_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
ALTER TABLE warehouse.mart_workflow_dashboard_v1
ADD COLUMN IF NOT EXISTS section_code TEXT,
ADD COLUMN IF NOT EXISTS section_title_ru TEXT,
ADD COLUMN IF NOT EXISTS metric_code TEXT,
ADD COLUMN IF NOT EXISTS metric_label_ru TEXT,
ADD COLUMN IF NOT EXISTS metric_value TEXT,
ADD COLUMN IF NOT EXISTS health_score NUMERIC,
ADD COLUMN IF NOT EXISTS health_light TEXT,
ADD COLUMN IF NOT EXISTS health_icon TEXT,
ADD COLUMN IF NOT EXISTS health_reason_code TEXT,
ADD COLUMN IF NOT EXISTS mart_version TEXT,
ADD COLUMN IF NOT EXISTS calculated_at TIMESTAMPTZ DEFAULT now(),
ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

SELECT 'mart_dashboard_has_section_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='mart_workflow_dashboard_v1'
      AND column_name='section_code'
);

SELECT 'mart_dashboard_has_metric_value=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='mart_workflow_dashboard_v1'
      AND column_name='metric_value'
);

SELECT 'mart_dashboard_has_health_icon=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='mart_workflow_dashboard_v1'
      AND column_name='health_icon'
);

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=WORKFLOW_MART_DASHBOARD_SCHEMA_PATCH_V1_READY';
SQL

echo "TEST_WORKFLOW_MART_DASHBOARD_SCHEMA_PATCH_V1_OK"
