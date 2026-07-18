BEGIN;
CREATE TABLE IF NOT EXISTS analytics.swing_paper_risk_policy_v1(
 policy_code text PRIMARY KEY,active boolean NOT NULL,policy jsonb NOT NULL,
 source_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE UNIQUE INDEX IF NOT EXISTS swing_paper_one_active_policy_v1 ON analytics.swing_paper_risk_policy_v1(active) WHERE active;
INSERT INTO analytics.swing_paper_risk_policy_v1(policy_code,active,policy,source_version)
VALUES('SWING_PAPER_RISK_V1',true,'{"paper_equity_rub":100000,"max_open_positions":3,"max_position_share":0.20,"max_margin_share":0.35,"max_daily_loss_share":0.02,"max_drawdown_share":0.10,"min_cash_reserve_share":0.30,"live_allowed":false}'::jsonb,'SWING_CANONICAL_PAPER_ENGINE_V1')
ON CONFLICT(policy_code) DO NOTHING;
UPDATE analytics.swing_paper_risk_policy_v1 SET policy=policy||'{"max_gross_leverage":3.0,"max_contracts_per_position":3}'::jsonb
 WHERE policy_code='SWING_PAPER_RISK_V1';

CREATE TABLE IF NOT EXISTS analytics.swing_paper_strategy_v1(
 process_id uuid PRIMARY KEY REFERENCES analytics.swing_candidate_lifecycle_v1(process_id),
 candidate_key bigint NOT NULL UNIQUE,strategy_family text NOT NULL,symbol text NOT NULL,timeframe text NOT NULL,
 parameter_snapshot jsonb NOT NULL,status_code text NOT NULL CHECK(status_code IN('ACTIVE','BLOCKED','STOPPED')),
 paper_allowed boolean NOT NULL DEFAULT true,live_allowed boolean NOT NULL DEFAULT false CHECK(NOT live_allowed),
 activated_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS analytics.swing_paper_order_v1(
 order_id uuid PRIMARY KEY,process_id uuid NOT NULL REFERENCES analytics.swing_paper_strategy_v1(process_id),
 signal_ts timestamptz NOT NULL,side text NOT NULL,quantity numeric NOT NULL,reference_price numeric NOT NULL,
 order_type text NOT NULL,order_status text NOT NULL,reason_code text NOT NULL,execution_contract jsonb NOT NULL,
 broker_order_sent boolean NOT NULL DEFAULT false CHECK(NOT broker_order_sent),
 live_allowed boolean NOT NULL DEFAULT false CHECK(NOT live_allowed),created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(process_id,signal_ts,side)
);
CREATE TABLE IF NOT EXISTS analytics.swing_paper_fill_v1(
 fill_id uuid PRIMARY KEY,order_id uuid NOT NULL UNIQUE REFERENCES analytics.swing_paper_order_v1(order_id),
 fill_ts timestamptz NOT NULL,fill_price numeric NOT NULL,quantity numeric NOT NULL,
 commission numeric NOT NULL,exchange_fee numeric NOT NULL,clearing_fee numeric NOT NULL,slippage numeric NOT NULL,
 source_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS analytics.swing_paper_position_v1(
 process_id uuid PRIMARY KEY REFERENCES analytics.swing_paper_strategy_v1(process_id),side text,quantity numeric NOT NULL DEFAULT 0,
 entry_ts timestamptz,entry_price numeric,last_price numeric,bars_held integer NOT NULL DEFAULT 0,
 status_code text NOT NULL CHECK(status_code IN('FLAT','OPEN')),entry_cost numeric NOT NULL DEFAULT 0,
 exposure_rub numeric NOT NULL DEFAULT 0,margin_used_rub numeric NOT NULL DEFAULT 0,
 unrealized_pnl numeric NOT NULL DEFAULT 0,updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS analytics.swing_paper_trade_v1(
 trade_id uuid PRIMARY KEY,process_id uuid NOT NULL REFERENCES analytics.swing_paper_strategy_v1(process_id),
 entry_order_id uuid NOT NULL REFERENCES analytics.swing_paper_order_v1(order_id),exit_order_id uuid NOT NULL REFERENCES analytics.swing_paper_order_v1(order_id),
 side text NOT NULL,quantity numeric NOT NULL,entry_ts timestamptz NOT NULL,exit_ts timestamptz NOT NULL,
 entry_price numeric NOT NULL,exit_price numeric NOT NULL,gross_pnl numeric NOT NULL,total_cost numeric NOT NULL,
 net_pnl numeric NOT NULL,estimated_tax numeric NOT NULL,net_after_tax numeric NOT NULL,exit_reason text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(process_id,entry_ts)
);
CREATE TABLE IF NOT EXISTS analytics.swing_paper_risk_decision_v1(
 decision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,process_id uuid NOT NULL,
 decision_code text NOT NULL,reason_codes jsonb NOT NULL,open_positions integer NOT NULL,
 gross_exposure_rub numeric NOT NULL,daily_pnl numeric NOT NULL,drawdown numeric NOT NULL,
 policy_snapshot jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS analytics.swing_paper_worker_state_v1(
 process_id uuid PRIMARY KEY,last_evaluated_ts timestamptz,worker_status text NOT NULL,last_error text,
 heartbeat_at timestamptz NOT NULL DEFAULT clock_timestamp(),updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE IF NOT EXISTS analytics.market_contract_cost_spec_v1(
 symbol text PRIMARY KEY,initial_margin numeric,buy_sell_fee numeric,scalper_fee numeric,
 negotiated_fee numeric,exercise_fee numeric,fee_currency text NOT NULL DEFAULT 'RUB',
 source_version text NOT NULL,source_payload jsonb NOT NULL,verified_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES('SWING_PAPER_ENGINE','SWING_PAPER_ENGINE_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,600,51,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES
 ('CONTRACT_SPEC_SYNC_NIGHT','CONTRACT_SPEC_SYNC_V1',true,'Europe/Moscow','[0,1,2,3,4]'::jsonb,time '00:05',time '08:30',1440,900,20,'V2_MARGIN_FEES'),
 ('CONTRACT_SPEC_SYNC_WEEKEND','CONTRACT_SPEC_SYNC_V1',true,'Europe/Moscow','[5,6]'::jsonb,time '00:00',time '23:59',1440,900,20,'V2_MARGIN_FEES')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
GRANT SELECT,INSERT,UPDATE ON analytics.swing_paper_risk_policy_v1,analytics.swing_paper_strategy_v1,
 analytics.swing_paper_order_v1,analytics.swing_paper_fill_v1,analytics.swing_paper_position_v1,
 analytics.swing_paper_trade_v1,analytics.swing_paper_risk_decision_v1,analytics.swing_paper_worker_state_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.market_contract_cost_spec_v1 TO alex;
GRANT USAGE,SELECT ON SEQUENCE analytics.swing_paper_risk_decision_v1_decision_id_seq TO alex;
INSERT INTO presentation.ui_resource_v1
 (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,resource_group,source_version)
VALUES
 ('status.completed','ru','Завершено','Завершено','Завершено','Этап завершён','status','SWING_PAPER_ENGINE_V1'),
 ('research.control.section.swing.lifecycle.title','ru','Swing · Paper','Swing','Swing','Автономный путь OOS → Forward → Shadow → Paper; LIVE отключён','research','SWING_PAPER_ENGINE_V1'),
 ('research.control.section.swing_lifecycle.title','ru','Swing · Paper','Swing','Swing','Автономный путь OOS → Forward → Shadow → Paper; LIVE отключён','research','SWING_PAPER_ENGINE_V1'),
 ('column.priority','ru','№','№','№','Приоритет исследования','column','SWING_PAPER_ENGINE_V1'),
 ('column.timeframe','ru','ТФ','ТФ','ТФ','Таймфрейм','column','SWING_PAPER_ENGINE_V1'),
 ('column.stage','ru','Этап','Этап','Этап','Этап жизненного цикла','column','SWING_PAPER_ENGINE_V1'),
 ('column.future.bars','ru','Накоплено','Накопл.','Накопл.','Накоплено будущих баров','column','SWING_PAPER_ENGINE_V1'),
 ('column.required.bars','ru','Нужно','Нужно','Нужно','Минимум будущих баров','column','SWING_PAPER_ENGINE_V1'),
 ('column.state','ru','Статус','Статус','Статус','Текущее состояние','column','SWING_PAPER_ENGINE_V1'),
 ('column.position','ru','Позиция','Позиция','Поз.','Состояние Paper-позиции','column','SWING_PAPER_ENGINE_V1'),
 ('column.paper.pnl','ru','Paper PnL','PnL','PnL','Финансовый результат модельных сделок','column','SWING_PAPER_ENGINE_V1'),
 ('column.risk','ru','Риск','Риск','Риск','Последнее решение риск-контроля','column','SWING_PAPER_ENGINE_V1')
 ,('status.edge_search_server_load_high','ru','Высокая нагрузка','Нагрузка','Нагрузка','Поиск отложен из-за высокой нагрузки сервера','status','SWING_PAPER_ENGINE_V1')
 ,('status.shadow_assessment_gap','ru','Не хватает Shadow-данных','Shadow','Shadow','Недостаточно независимых Shadow-наблюдений для решения','status','SWING_PAPER_ENGINE_V1')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,resource_group=excluded.resource_group,
 source_version=excluded.source_version,updated_at=now();
COMMIT;
