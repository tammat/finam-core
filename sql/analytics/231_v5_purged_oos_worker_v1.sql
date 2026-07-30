BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_oos_run_v1 (
    run_id uuid PRIMARY KEY,
    admission_id uuid NOT NULL UNIQUE REFERENCES analytics.trade_outcome_oos_admission_v1(admission_id),
    hypothesis_id uuid NOT NULL,
    purge_before_ts timestamptz NOT NULL,
    confirmation_after_ts timestamptz NOT NULL,
    embargo_seconds integer NOT NULL CHECK (embargo_seconds >= 0),
    minimum_observations integer NOT NULL DEFAULT 20 CHECK (minimum_observations > 0),
    status_code text NOT NULL CHECK (status_code IN ('COLLECTING','OOS_PASS','OOS_FAIL','ERROR')),
    observations_included integer NOT NULL DEFAULT 0,
    observations_excluded integer NOT NULL DEFAULT 0,
    net_pnl numeric,
    expectancy numeric,
    profit_factor numeric,
    reason_code text NOT NULL DEFAULT 'WAITING_FUTURE_OBSERVATIONS',
    source_version text NOT NULL DEFAULT 'V5_PURGED_OOS_WORKER_V1',
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.v5_oos_observation_audit_v1 (
    audit_id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES analytics.v5_oos_run_v1(run_id),
    admission_id uuid NOT NULL,
    source_trade_id bigint NOT NULL REFERENCES public.closed_trades(id),
    signal_id text,
    entry_ts timestamptz NOT NULL,
    exit_ts timestamptz NOT NULL,
    decision_code text NOT NULL CHECK (decision_code IN (
        'INCLUDED','EXCLUDED_PRE_BOUNDARY','EXCLUDED_EMBARGO_OR_OVERLAP',
        'EXCLUDED_CONTEXT','EXCLUDED_REUSED'
    )),
    reason_code text NOT NULL,
    net_pnl numeric,
    source_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    audited_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(run_id,source_trade_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS v5_oos_included_trade_once_idx
ON analytics.v5_oos_observation_audit_v1(source_trade_id)
WHERE decision_code='INCLUDED';

CREATE INDEX IF NOT EXISTS v5_oos_audit_run_decision_idx
ON analytics.v5_oos_observation_audit_v1(run_id,decision_code,entry_ts);

ALTER TABLE analytics.trade_outcome_oos_admission_v1
    DROP CONSTRAINT IF EXISTS trade_outcome_oos_admission_v1_status_code_check;
ALTER TABLE analytics.trade_outcome_oos_admission_v1
    ADD CONSTRAINT trade_outcome_oos_admission_v1_status_code_check
    CHECK (status_code IN (
        'WAITING_HYPOTHESIS','WAITING_FRESH_DATA','WAITING_CONTEXT',
        'WAITING_MICROSTRUCTURE','REJECTED_COSTS','QUEUED','RUNNING',
        'OOS_PASS','OOS_FAIL','ERROR','CLOSED'
    ));

CREATE OR REPLACE VIEW analytics.closed_trades_fresh_v5_training_v1 AS
SELECT c.*
FROM analytics.closed_trades_fresh_v5_confirmed c
WHERE NOT EXISTS (
    SELECT 1
    FROM analytics.trade_outcome_oos_admission_v1 a
    WHERE a.status_code IN ('QUEUED','RUNNING','OOS_PASS','OOS_FAIL')
      AND c.exit_ts > (a.oos_request->'temporal_isolation'->>'purge_before_ts')::timestamptz
      AND c.symbol = a.oos_request->>'symbol'
      AND coalesce(nullif(c.strategy,''),'UNASSIGNED') = a.oos_request->>'paper_strategy_code'
      AND upper(coalesce(nullif(c.side,''),'UNKNOWN')) = upper(a.oos_request->>'side_code')
);

COMMENT ON VIEW analytics.closed_trades_fresh_v5_training_v1 IS
'Замороженная V5 training-когорта: сделки после purge_before_ts активного OOS admission исключены.';

GRANT SELECT,INSERT,UPDATE ON analytics.v5_oos_run_v1 TO alex,finam;
GRANT SELECT,INSERT ON analytics.v5_oos_observation_audit_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.v5_oos_observation_audit_v1_audit_id_seq TO alex,finam;
GRANT SELECT ON analytics.closed_trades_fresh_v5_training_v1 TO alex,finam;

COMMIT;
