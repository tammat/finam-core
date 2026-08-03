BEGIN;

CREATE TABLE IF NOT EXISTS analytics.reachable_shadow_morning_audit_v1 (
    audit_id bigserial PRIMARY KEY,
    checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    status_code text NOT NULL CHECK (status_code IN ('READY','ATTENTION','BLOCK')),
    reason_codes text[] NOT NULL DEFAULT '{}'::text[],
    challenger_count integer NOT NULL,
    fresh_symbol_count integer NOT NULL,
    matched_count integer NOT NULL,
    entered_count integer NOT NULL,
    completed_count integer NOT NULL,
    pre_freeze_excluded_count integer NOT NULL,
    paper_allowed_count integer NOT NULL,
    real_allowed_count integer NOT NULL,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_version text NOT NULL
);

CREATE INDEX IF NOT EXISTS reachable_shadow_morning_audit_checked_idx
  ON analytics.reachable_shadow_morning_audit_v1 (checked_at DESC);

COMMIT;
