BEGIN;

CREATE TABLE IF NOT EXISTS analytics.research_global_experiment_v1 (
 experiment_no bigserial PRIMARY KEY,
 experiment_id uuid NOT NULL UNIQUE,
 scenario_run_id uuid NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
 search_run_id uuid NOT NULL,
 result_id uuid NOT NULL REFERENCES analytics.walkforward_edge_search_v3(result_id),
 asset_class text NOT NULL,
 hypothesis_code text NOT NULL,
 strategy_code text NOT NULL,
 symbol text NOT NULL,
 timeframe text NOT NULL,
 parameter_hash text NOT NULL,
 raw_p_value numeric NOT NULL CHECK(raw_p_value BETWEEN 0 AND 1),
 cumulative_trials bigint NOT NULL,
 adjusted_p_value numeric NOT NULL CHECK(adjusted_p_value BETWEEN 0 AND 1),
 verdict_code text NOT NULL CHECK(verdict_code IN ('PASS','FAIL')),
 reason_code text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(scenario_run_id,result_id)
);
CREATE INDEX IF NOT EXISTS research_global_experiment_lookup_v1
 ON analytics.research_global_experiment_v1(asset_class,hypothesis_code,symbol,created_at DESC);

CREATE TABLE IF NOT EXISTS analytics.research_holdout_snapshot_v1 (
 holdout_id uuid PRIMARY KEY,
 owner_search_run_id uuid NOT NULL,
 symbol text NOT NULL,
 timeframe text NOT NULL,
 holdout_start timestamptz NOT NULL,
 holdout_end timestamptz NOT NULL CHECK(holdout_end > holdout_start),
 data_watermark timestamptz NOT NULL,
 state_code text NOT NULL CHECK(state_code IN ('OPENED','RETIRED')) DEFAULT 'OPENED',
 opened_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(owner_search_run_id,symbol,timeframe,holdout_start,holdout_end)
);
CREATE INDEX IF NOT EXISTS research_holdout_overlap_lookup_v1
 ON analytics.research_holdout_snapshot_v1(symbol,timeframe,holdout_start,holdout_end);

CREATE TABLE IF NOT EXISTS analytics.pnl_unit_audit_v1 (
 audit_id uuid PRIMARY KEY,
 scenario_run_id uuid NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
 symbol text NOT NULL,
 asset_class text NOT NULL,
 lot_size numeric,
 tick_size numeric,
 tick_value numeric,
 contract_multiplier numeric,
 quantity_step numeric,
 underlying_units numeric,
 margin_currency text,
 check_results jsonb NOT NULL,
 status_code text NOT NULL CHECK(status_code IN ('READY','BLOCKED')),
 reason_codes jsonb NOT NULL,
 audited_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(scenario_run_id,symbol)
);

CREATE TABLE IF NOT EXISTS analytics.edge_economic_hypothesis_contract_v1 (
 hypothesis_code text PRIMARY KEY,
 asset_scope text NOT NULL,
 title_ru text NOT NULL,
 economic_rationale_ru text NOT NULL,
 required_features jsonb NOT NULL,
 research_family text NOT NULL,
 priority integer NOT NULL CHECK(priority BETWEEN 1 AND 100),
 enabled boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.edge_economic_hypothesis_contract_v1
 (hypothesis_code,asset_scope,title_ru,economic_rationale_ru,required_features,research_family,priority)
VALUES
 ('EQUITY_CROSS_SECTION_MOMENTUM','EQUITY','Лидеры акций','Устойчивость относительной силы ликвидных акций после издержек.','["returns","turnover","corporate_actions"]','CROSS_SECTION',90),
 ('EQUITY_LIQUIDITY_REVERSION','EQUITY','Откат акций','Компенсация временного дисбаланса ликвидности без ловли структурного падения.','["spread","turnover","volatility","market_beta"]','LIQUIDITY_REVERSION',80),
 ('EQUITY_EVENT_GAP','EQUITY','События акций','Проверка продолжения и закрытия гэпа с учётом дивидендов и корпоративных событий.','["corporate_actions","overnight_gap","volume"]','EVENT',65),
 ('FUTURES_CARRY_ROLL','FUTURES','Кэрри фьючерсов','Доходность формы кривой и роллирования после стоимости переноса и смены контракта.','["current_contract","next_contract","expiry","term_structure"]','CARRY_ROLL',95),
 ('FUTURES_CALENDAR_SEASONALITY','FUTURES','Сезонность','Повторяемые календарные и экспирационные эффекты без утечки будущего.','["session","weekday","month","days_to_expiry"]','SEASONALITY',75),
 ('CROSS_ASSET_RELATIVE_VALUE','ALL','Спреды','Возврат экономически связанных спредов с контролем стабильности хеджа.','["paired_prices","hedge_ratio","cointegration","borrow_or_margin"]','RELATIVE_VALUE',85)
ON CONFLICT(hypothesis_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS analytics.edge_portfolio_selection_v1 (
 selection_id uuid PRIMARY KEY,
 scenario_run_id uuid NOT NULL REFERENCES analytics.edge_search_scenario_run_v1(run_id),
 evaluation_id uuid NOT NULL REFERENCES analytics.edge_methodology_evaluation_v1(evaluation_id),
 symbol text NOT NULL,
 strategy_code text NOT NULL,
 asset_class text NOT NULL,
 marginal_correlation numeric,
 risk_weight numeric NOT NULL DEFAULT 0,
 capacity_weight numeric NOT NULL DEFAULT 0,
 selected boolean NOT NULL DEFAULT false,
 reason_code text NOT NULL,
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(scenario_run_id,evaluation_id)
);

ALTER TABLE analytics.edge_methodology_evaluation_v1
 ADD COLUMN IF NOT EXISTS global_experiment_no bigint,
 ADD COLUMN IF NOT EXISTS global_adjusted_p numeric,
 ADD COLUMN IF NOT EXISTS holdout_access_code text,
 ADD COLUMN IF NOT EXISTS pnl_unit_status text;

DELETE FROM analytics.edge_search_scenario_step_v1
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH'
  AND executor_code IN ('AUDIT_PNL_UNITS','SYNC_ECONOMIC_HYPOTHESES','GOVERN_EXPERIMENTS');

UPDATE analytics.edge_search_scenario_step_v1
SET step_order=step_order+100
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND step_order<100;

UPDATE analytics.edge_search_scenario_step_v1 SET step_order=1 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='SYNC_CONTRACT_SPECS';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=3 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='RESOLVE_FUTURES_ROLL';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=5 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='DISCOVER_REGIME';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=6 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='WALKFORWARD';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=8 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='METHODOLOGY_GATE';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=9 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='PROMOTE_OOS';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=10 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='VALIDATE_EDGE';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=11 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='OOS_FORWARD_HANDOFF';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=12 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='ADMIT_FORWARD';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=13 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='OBSERVE_FORWARD';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=14 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='PROJECT_SHADOW';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=15 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='ADMIT_PAPER';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=16 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='BUILD_LINEAGE';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=17 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='ANALYZE_RESULTS';
UPDATE analytics.edge_search_scenario_step_v1 SET step_order=18 WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='GENERATE_ADAPTIVE_SCENARIOS';

INSERT INTO analytics.edge_search_scenario_step_v1
 (scenario_code,step_order,executor_code,title_ru,enabled,timeout_seconds,required)
VALUES
 ('AUTONOMOUS_EDGE_SEARCH',2,'AUDIT_PNL_UNITS','Аудит P&L',true,180,true),
 ('AUTONOMOUS_EDGE_SEARCH',4,'SYNC_ECONOMIC_HYPOTHESES','Экономические гипотезы',true,180,true),
 ('AUTONOMOUS_EDGE_SEARCH',7,'GOVERN_EXPERIMENTS','Испытания и holdout',true,300,true)
ON CONFLICT(scenario_code,step_order) DO UPDATE SET
 executor_code=EXCLUDED.executor_code,title_ru=EXCLUDED.title_ru,enabled=true,
 timeout_seconds=EXCLUDED.timeout_seconds,required=true;

UPDATE analytics.edge_search_scenario_v1
SET config_version='V5_GLOBAL_RESEARCH_GOVERNANCE',updated_at=clock_timestamp()
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH';

GRANT SELECT,INSERT,UPDATE ON analytics.research_global_experiment_v1,
 analytics.research_holdout_snapshot_v1,analytics.pnl_unit_audit_v1,
 analytics.edge_portfolio_selection_v1 TO alex;
GRANT SELECT ON analytics.edge_economic_hypothesis_contract_v1 TO alex;
GRANT USAGE,SELECT ON SEQUENCE analytics.research_global_experiment_v1_experiment_no_seq TO alex;

COMMIT;
