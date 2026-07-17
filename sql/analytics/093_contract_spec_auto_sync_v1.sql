BEGIN;

CREATE TABLE IF NOT EXISTS analytics.contract_spec_sync_run_v1 (
    run_id uuid PRIMARY KEY,
    status_code text NOT NULL,
    symbols_total integer NOT NULL DEFAULT 0,
    symbols_written integer NOT NULL DEFAULT 0,
    symbols_unchanged integer NOT NULL DEFAULT 0,
    symbols_failed integer NOT NULL DEFAULT 0,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.contract_spec_sync_item_v1 (
    item_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES analytics.contract_spec_sync_run_v1(run_id),
    symbol text NOT NULL,
    status_code text NOT NULL,
    reason_code text NOT NULL,
    source_version text NOT NULL,
    source_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(run_id,symbol)
);

DO $$ BEGIN
 IF NOT EXISTS (SELECT 1 FROM analytics.edge_search_scenario_step_v1
                WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='SYNC_CONTRACT_SPECS') THEN
   UPDATE analytics.edge_search_scenario_step_v1 SET step_order=step_order+100
    WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';
   UPDATE analytics.edge_search_scenario_step_v1 SET step_order=step_order-99
    WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';
 END IF;
END $$;

INSERT INTO analytics.edge_search_scenario_step_v1
(scenario_code,step_order,executor_code,title_ru,timeout_seconds,required,enabled)
VALUES('AUTONOMOUS_EDGE_SEARCH',1,'SYNC_CONTRACT_SPECS','Сверка спецификаций',300,true,true)
ON CONFLICT(scenario_code,step_order) DO UPDATE SET executor_code=EXCLUDED.executor_code,
 title_ru=EXCLUDED.title_ru,timeout_seconds=EXCLUDED.timeout_seconds,
 required=EXCLUDED.required,enabled=EXCLUDED.enabled;

CREATE OR REPLACE VIEW analytics.contract_spec_sync_health_v1 AS
WITH required AS (
 SELECT count(DISTINCT symbol) required_count FROM public.market_bars
 WHERE timeframe='M5' AND ts>=clock_timestamp()-interval '7 days'
   AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
   AND (symbol LIKE '%@MISX' OR symbol LIKE '%@RTSX')
), ready AS (
 SELECT count(DISTINCT s.symbol) ready_count FROM analytics.market_contract_spec_v1 s
 JOIN (SELECT DISTINCT symbol FROM public.market_bars WHERE timeframe='M5'
       AND ts>=clock_timestamp()-interval '7 days') m USING(symbol)
 WHERE s.is_active AND s.source_version='MOEX_ISS_CONTRACT_SPEC_V1'
), latest AS (
 SELECT * FROM analytics.contract_spec_sync_run_v1 ORDER BY started_at DESC LIMIT 1
)
SELECT r.required_count,d.ready_count,r.required_count-d.ready_count missing_count,
       l.status_code,l.symbols_failed,l.started_at,l.finished_at,
       CASE WHEN d.ready_count=r.required_count AND coalesce(l.symbols_failed,0)=0
            THEN 'READY' ELSE 'PARTIAL' END health_code
FROM required r CROSS JOIN ready d LEFT JOIN latest l ON true;

CREATE OR REPLACE VIEW analytics.execution_model_health_v1 AS
WITH quote_health AS (
    SELECT count(DISTINCT symbol) AS quote_symbols,max(observed_at) AS latest_quote_at,
           count(*) FILTER (WHERE best_bid>0 AND best_ask>=best_bid) AS valid_quotes
    FROM analytics.market_microstructure_snapshot_v1
), sync AS (SELECT * FROM analytics.contract_spec_sync_health_v1), active_policy AS (
    SELECT policy_code,policy_hash,activated_at FROM analytics.execution_simulation_policy_v1 WHERE active
)
SELECT p.policy_code,p.policy_hash,p.activated_at,q.quote_symbols,q.latest_quote_at,q.valid_quotes,
       s.required_count AS market_count,s.ready_count AS spec_count,
       CASE WHEN q.latest_quote_at>=clock_timestamp()-interval '5 minutes' THEN 'READY' ELSE 'STALE' END AS quote_status,
       s.health_code AS spec_status
FROM active_policy p CROSS JOIN quote_health q CROSS JOIN sync s;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.domain.sync_contract_specs','ru','Спецификации','Спец.','Спец.','Автоматическая сверка лотов, шага цены и стоимости шага с MOEX ISS','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip;

COMMIT;
