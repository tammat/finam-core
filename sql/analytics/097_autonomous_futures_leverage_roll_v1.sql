BEGIN;

CREATE TABLE IF NOT EXISTS analytics.market_contract_execution_spec_v2 (
 symbol text PRIMARY KEY,quantity_step numeric NOT NULL,underlying_units numeric NOT NULL,
 source_version text NOT NULL,updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(quantity_step>0),CHECK(underlying_units>0)
);
INSERT INTO analytics.market_contract_execution_spec_v2
(symbol,quantity_step,underlying_units,source_version)
SELECT symbol,CASE WHEN symbol LIKE '%@RTSX' THEN 1 ELSE lot_size END,
 CASE WHEN symbol LIKE '%@RTSX' THEN lot_size ELSE 1 END,'CONTRACT_EXECUTION_SPEC_V2'
FROM analytics.market_contract_spec_v1 WHERE is_active
ON CONFLICT(symbol) DO NOTHING;

CREATE TABLE IF NOT EXISTS analytics.futures_autonomy_policy_v1 (
 policy_code text PRIMARY KEY,active boolean NOT NULL DEFAULT false,policy jsonb NOT NULL,
 policy_hash text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 CHECK(jsonb_typeof(policy)='object')
);
CREATE UNIQUE INDEX IF NOT EXISTS futures_autonomy_one_active_v1
 ON analytics.futures_autonomy_policy_v1(active) WHERE active;
INSERT INTO analytics.futures_autonomy_policy_v1(policy_code,active,policy,policy_hash)
VALUES('FUTURES_AUTONOMY_V1',true,'{
 "roots":["BR","NG"],"roll_days_before_expiry":5,"next_volume_ratio":1.0,
 "minimum_bars":6000,"volume_window_days":5,
 "research_equity_rub":100000,"max_gross_leverage":3.0,
 "max_position_share":0.35,"max_margin_share":0.35
}'::jsonb,md5('{
 "roots":["BR","NG"],"roll_days_before_expiry":5,"next_volume_ratio":1.0,
 "minimum_bars":6000,"volume_window_days":5,
 "research_equity_rub":100000,"max_gross_leverage":3.0,
 "max_position_share":0.35,"max_margin_share":0.35
}'::jsonb::text)) ON CONFLICT(policy_code) DO UPDATE SET active=true;

CREATE OR REPLACE FUNCTION analytics.guard_futures_autonomy_policy_v1()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF OLD.policy IS DISTINCT FROM NEW.policy OR OLD.policy_hash IS DISTINCT FROM NEW.policy_hash
 THEN RAISE EXCEPTION 'FUTURES_AUTONOMY_POLICY_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS futures_autonomy_policy_guard_v1 ON analytics.futures_autonomy_policy_v1;
CREATE TRIGGER futures_autonomy_policy_guard_v1 BEFORE UPDATE ON analytics.futures_autonomy_policy_v1
FOR EACH ROW EXECUTE FUNCTION analytics.guard_futures_autonomy_policy_v1();

CREATE TABLE IF NOT EXISTS analytics.futures_roll_decision_v1 (
 decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,run_id uuid NOT NULL,
 policy_code text NOT NULL REFERENCES analytics.futures_autonomy_policy_v1(policy_code),
 root_symbol text NOT NULL,current_symbol text,next_symbol text,selected_symbol text NOT NULL,
 current_expiration date,next_expiration date,days_to_expiry integer NOT NULL,
 current_median_volume numeric NOT NULL,next_median_volume numeric NOT NULL,
 decision_code text NOT NULL,candidates jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(run_id,root_symbol)
);
CREATE INDEX IF NOT EXISTS futures_roll_decision_latest_v1
 ON analytics.futures_roll_decision_v1(root_symbol,created_at DESC);

UPDATE analytics.execution_simulation_policy_v1 SET active=false WHERE active;
INSERT INTO analytics.execution_simulation_policy_v1(policy_code,active,policy,policy_hash)
VALUES('REALISTIC_EXECUTION_V2_FUTURES_LEVERAGE',true,'{
 "signal_latency_bars":1,"max_participation_rate":0.01,"minimum_fill_ratio":0.25,
 "research_equity_rub":100000,"max_gross_leverage":3.0,"max_position_share":0.35,
 "max_margin_share":0.35,"fallback_spread_bps":8.0,"impact_bps_at_max_participation":4.0,
 "stress_cost_multiplier":1.5,"max_fallback_quote_share":1.0,
 "quote_estimator":"P90_LAST_10000","require_contract_spec":true
}'::jsonb,md5('{
 "signal_latency_bars":1,"max_participation_rate":0.01,"minimum_fill_ratio":0.25,
 "research_equity_rub":100000,"max_gross_leverage":3.0,"max_position_share":0.35,
 "max_margin_share":0.35,"fallback_spread_bps":8.0,"impact_bps_at_max_participation":4.0,
 "stress_cost_multiplier":1.5,"max_fallback_quote_share":1.0,
 "quote_estimator":"P90_LAST_10000","require_contract_spec":true
}'::jsonb::text)) ON CONFLICT(policy_code) DO UPDATE SET active=true;

DO $$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM analytics.edge_search_scenario_step_v1
   WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='RESOLVE_FUTURES_ROLL') THEN
  UPDATE analytics.edge_search_scenario_step_v1 SET step_order=step_order+100
   WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order>=2;
  UPDATE analytics.edge_search_scenario_step_v1 SET step_order=step_order-99
   WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order>=102;
  INSERT INTO analytics.edge_search_scenario_step_v1
   (scenario_code,step_order,executor_code,title_ru,timeout_seconds,required,enabled)
  VALUES('AUTONOMOUS_EDGE_SEARCH',2,'RESOLVE_FUTURES_ROLL','Выбор фьючерсного контракта',300,true,true);
 END IF;
END $$;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.futures.roll','ru','Роллирование','Ролл','Ролл','Автоматический выбор рабочего фьючерсного контракта по сроку и ликвидности','','research'),
('research.futures.leverage','ru','Плечо','Плечо','Плечо','Размер позиции ограничивается плечом, риском, ГО и ликвидностью','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.universe.reason.rollover_contract_not_selected','ru','Другой контракт','Ролл','Ролл','Контракт исключён автоматическим решением о роллировании','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip;

COMMIT;
