BEGIN;

CREATE TABLE IF NOT EXISTS analytics.execution_simulation_policy_v1 (
    policy_code text PRIMARY KEY,
    active boolean NOT NULL DEFAULT false,
    policy jsonb NOT NULL,
    policy_hash text NOT NULL,
    activated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (jsonb_typeof(policy)='object')
);

CREATE UNIQUE INDEX IF NOT EXISTS execution_simulation_one_active_v1
    ON analytics.execution_simulation_policy_v1(active) WHERE active;

INSERT INTO analytics.execution_simulation_policy_v1(policy_code,active,policy,policy_hash)
VALUES ('REALISTIC_EXECUTION_V1',true,jsonb_build_object(
    'signal_latency_bars',1,
    'max_participation_rate',0.01,
    'minimum_fill_ratio',0.25,
    'target_notional_rub',100000,
    'fallback_spread_bps',8.0,
    'impact_bps_at_max_participation',4.0,
    'stress_cost_multiplier',1.5,
    'max_fallback_quote_share',1.0,
    'quote_estimator','P90_LAST_10000',
    'require_contract_spec',true
),md5(jsonb_build_object(
    'signal_latency_bars',1,'max_participation_rate',0.01,'minimum_fill_ratio',0.25,
    'target_notional_rub',100000,'fallback_spread_bps',8.0,
    'impact_bps_at_max_participation',4.0,'stress_cost_multiplier',1.5,
    'max_fallback_quote_share',1.0,'quote_estimator','P90_LAST_10000',
    'require_contract_spec',true
)::text))
ON CONFLICT(policy_code) DO NOTHING;

CREATE OR REPLACE FUNCTION analytics.reject_execution_policy_mutation_v1()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.policy IS DISTINCT FROM NEW.policy OR OLD.policy_hash IS DISTINCT FROM NEW.policy_hash THEN
        RAISE EXCEPTION 'EXECUTION_SIMULATION_POLICY_IMMUTABLE';
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS execution_simulation_policy_immutable_v1 ON analytics.execution_simulation_policy_v1;
CREATE TRIGGER execution_simulation_policy_immutable_v1
BEFORE UPDATE ON analytics.execution_simulation_policy_v1
FOR EACH ROW EXECUTE FUNCTION analytics.reject_execution_policy_mutation_v1();

CREATE TABLE IF NOT EXISTS analytics.research_trade_execution_audit_v1 (
    audit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_uuid uuid NOT NULL,
    trade_no integer NOT NULL,
    quantity numeric NOT NULL,
    fill_ratio numeric NOT NULL,
    spread_cost numeric NOT NULL,
    impact_cost numeric NOT NULL,
    latency_bars integer NOT NULL,
    quote_source text NOT NULL,
    capacity_rub numeric NOT NULL,
    contract_spec_source text NOT NULL,
    execution_policy_code text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(run_uuid,trade_no)
);

CREATE OR REPLACE VIEW analytics.execution_model_health_v1 AS
WITH quote_health AS (
    SELECT count(DISTINCT symbol) AS quote_symbols,
           max(observed_at) AS latest_quote_at,
           count(*) FILTER (WHERE best_bid>0 AND best_ask>=best_bid) AS valid_quotes
    FROM analytics.market_microstructure_snapshot_v1
), research_markets AS (
    SELECT count(DISTINCT symbol) AS market_count
    FROM public.market_bars
    WHERE timeframe='M5' AND ts>=clock_timestamp()-interval '7 days'
      AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
), specs AS (
    SELECT count(DISTINCT symbol) AS spec_count
    FROM analytics.market_contract_spec_v1 WHERE is_active
), active_policy AS (
    SELECT policy_code,policy_hash,activated_at FROM analytics.execution_simulation_policy_v1 WHERE active
)
SELECT p.policy_code,p.policy_hash,p.activated_at,q.quote_symbols,q.latest_quote_at,q.valid_quotes,
       r.market_count,s.spec_count,
       CASE WHEN q.latest_quote_at>=clock_timestamp()-interval '5 minutes' THEN 'READY' ELSE 'STALE' END AS quote_status,
       CASE WHEN s.spec_count>=r.market_count THEN 'READY' ELSE 'PARTIAL' END AS spec_status
FROM active_policy p CROSS JOIN quote_health q CROSS JOIN research_markets r CROSS JOIN specs s;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.execution_quotes','ru','Котировки исполнения','Котировки','Котир.','Число инструментов с bid/ask; цвет показывает свежесть потока','','research'),
('research.tile.execution_specs','ru','Спецификации','Спецификации','Спец.','Число инструментов со справочником лота, тика и множителя контракта','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

COMMIT;
