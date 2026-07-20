BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_search_resource_policy_v1(
  branch_code text PRIMARY KEY,
  resource_share_pct numeric(5,2) NOT NULL CHECK(resource_share_pct>0 AND resource_share_pct<=100),
  variant_budget integer NOT NULL CHECK(variant_budget>0),
  priority integer NOT NULL,
  policy_json jsonb NOT NULL CHECK(jsonb_typeof(policy_json)='object'),
  enabled boolean NOT NULL DEFAULT true,
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.edge_search_resource_policy_v1
(branch_code,resource_share_pct,variant_budget,priority,policy_json)
VALUES
('COST_REMEDIATION',70,34,10,'{"strict_costs":true,"empirical_bid_ask":true,"max_hold_bars":20,"coarse_folds":2,"full_oos_top_share":0.10,"fingerprint_reuse":false}'::jsonb),
('SAMPLE_EXPANSION',20,10,20,'{"continuous_futures":true,"compatible_regimes_only":true,"rare_entry_early_stop":true,"coarse_folds":2,"full_oos_top_share":0.10,"fingerprint_reuse":false}'::jsonb),
('NEW_INSTRUMENT_EXPLORATION',10,4,30,'{"scout_selected_only":true,"specification_required":true,"liquidity_required":true,"history_required":true,"coarse_only":true}'::jsonb)
ON CONFLICT(branch_code) DO UPDATE SET resource_share_pct=excluded.resource_share_pct,
 variant_budget=excluded.variant_budget,priority=excluded.priority,
 policy_json=excluded.policy_json,enabled=true,updated_at=clock_timestamp();

CREATE OR REPLACE VIEW analytics.zero_cost_diagnostic_summary_v1 AS
WITH latest AS (
  SELECT search_run_id FROM analytics.walkforward_edge_search_v3
  GROUP BY search_run_id ORDER BY max(created_at) DESC LIMIT 1
), evaluated AS (
  SELECT w.* FROM analytics.walkforward_edge_search_v3 w JOIN latest l USING(search_run_id)
)
SELECT search_run_id AS process_id,count(*)::bigint AS evaluated_variants,
       count(*) FILTER(WHERE oos_gross_passed)::bigint AS gross_pass,
       count(*) FILTER(WHERE cost_adjusted_passed)::bigint AS after_costs_pass,
       count(*) FILTER(WHERE oos_gross_passed AND NOT cost_adjusted_passed)::bigint AS cost_lost,
       max(created_at) AS updated_at
FROM evaluated GROUP BY search_run_id;

CREATE OR REPLACE VIEW analytics.edge_search_resource_allocation_v1 AS
WITH latest_scout AS (
  SELECT run_id FROM analytics.instrument_scout_run_v1 ORDER BY started_at DESC LIMIT 1
), scout AS (
  SELECT count(DISTINCT r.symbol) FILTER(WHERE r.decision_code='SELECTED' AND r.funnel_stage_code='COARSE_SEARCH')::bigint sources,
         count(DISTINCT q.symbol) FILTER(WHERE q.action_code='RESEARCH_NEXT' AND q.status_code IN ('PENDING','RUNNING','APPLIED'))::bigint queued,
         max(greatest(r.created_at,q.updated_at)) updated_at
  FROM analytics.instrument_scout_result_v1 r JOIN latest_scout l USING(run_id)
  LEFT JOIN analytics.instrument_scout_queue_v1 q ON q.run_id=r.run_id AND q.symbol=r.symbol
)
SELECT p.branch_code,p.resource_share_pct,p.variant_budget,p.priority,p.policy_json,
       CASE WHEN p.branch_code='NEW_INSTRUMENT_EXPLORATION' THEN least(coalesce(s.sources,0),p.variant_budget)::bigint
            ELSE least(coalesce(b.created_variants,0),p.variant_budget)::bigint END allocated_variants,
       CASE WHEN p.branch_code='NEW_INSTRUMENT_EXPLORATION' THEN least(coalesce(s.queued,0),p.variant_budget)::bigint
            ELSE least(coalesce(b.queued_variants,0),p.variant_budget)::bigint END active_variants,
       coalesce(b.updated_at,s.updated_at,p.updated_at) updated_at
FROM analytics.edge_search_resource_policy_v1 p
LEFT JOIN analytics.oos_remediation_branch_summary_v1 b USING(branch_code)
CROSS JOIN scout s WHERE p.enabled;

CREATE OR REPLACE VIEW analytics.oos_remediation_branch_panel_v1 AS
SELECT process_id,branch_code,process_status,current_step_code,progress_pct,
       started_at,updated_at,source_failures,created_variants,pruned_variants,
       queued_variants,evaluated_variants,oos_pass,
       0::bigint AS gross_pass,0::bigint AS after_costs_pass,0::bigint AS cost_lost,
       false AS diagnostic_only
FROM analytics.oos_remediation_branch_summary_v1
UNION ALL
SELECT z.process_id,'ZERO_COST_DIAGNOSTIC'::text,'COMPLETE'::text,
       'PROMOTION_FORBIDDEN'::text,100::numeric,z.updated_at,z.updated_at,
       z.evaluated_variants,z.evaluated_variants,0::bigint,0::bigint,
       z.evaluated_variants,0::bigint,z.gross_pass,z.after_costs_pass,z.cost_lost,true
FROM analytics.zero_cost_diagnostic_summary_v1 z
UNION ALL
SELECT coalesce((SELECT run_id FROM analytics.instrument_scout_run_v1 ORDER BY started_at DESC LIMIT 1),
                '00000000-0000-0000-0000-000000000000'::uuid),
       'NEW_INSTRUMENT_EXPLORATION','MONITORING','SCOUT_TO_COARSE_SEARCH',
       CASE WHEN a.variant_budget>0 THEN round(100*a.active_variants/a.variant_budget,2) ELSE 0 END,
       a.updated_at,a.updated_at,a.allocated_variants,a.allocated_variants,0::bigint,
       a.active_variants,0::bigint,0::bigint,0::bigint,0::bigint,0::bigint,false
FROM analytics.edge_search_resource_allocation_v1 a
WHERE a.branch_code='NEW_INSTRUMENT_EXPLORATION';

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.remediation.branch.zero_cost_diagnostic','ru','Без издержек','Без издержек','Без изд.','Диагностика валового edge без права продвижения','','research'),
('research.remediation.branch.new_instrument_exploration','ru','Новые рынки','Новые рынки','Нов.','10% вычислительного бюджета на новые ликвидные инструменты и семейства','','research'),
('research.remediation.column.gross','ru','До изд.','До изд.','Вал.','Прошли OOS до комиссии, спреда и проскальзывания','','research'),
('research.remediation.column.net','ru','После изд.','После изд.','Чист.','Прошли OOS после реальных издержек','','research'),
('research.remediation.column.lost','ru','Потеря','Потеря','Пот.','Потеряли PASS именно при учёте издержек','','research'),
('research.remediation.diagnostic','ru','Только анализ','Анализ','Анализ','Диагностическая ветка не может продвигать кандидатов','','research'),
('research.domain.complete','ru','Готово','Готово','Готово','Диагностический расчёт завершён','','research'),
('research.remediation.branch.zero_cost_diagnostic','en','Zero-cost diagnostic','Zero cost','Gross','Gross-edge diagnostic with promotion disabled','','research'),
('research.remediation.branch.new_instrument_exploration','en','New markets','New markets','New','10% compute budget for new liquid instruments and families','','research'),
('research.remediation.column.gross','en','Before costs','Gross','Gross','Passed OOS before commission, spread and slippage','','research'),
('research.remediation.column.net','en','After costs','Net','Net','Passed OOS after realistic costs','','research'),
('research.remediation.column.lost','en','Cost loss','Lost','Lost','Lost PASS specifically because of costs','','research'),
('research.remediation.diagnostic','en','Analysis only','Analysis','Analysis','Diagnostic branch cannot promote candidates','','research'),
('research.domain.complete','en','Complete','Complete','Done','Diagnostic calculation completed','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,
 caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,icon=excluded.icon,resource_group=excluded.resource_group;

GRANT SELECT ON analytics.zero_cost_diagnostic_summary_v1 TO alex,finam;
GRANT SELECT ON analytics.oos_remediation_branch_panel_v1 TO alex,finam;
GRANT SELECT ON analytics.edge_search_resource_policy_v1 TO alex,finam;
GRANT SELECT ON analytics.edge_search_resource_allocation_v1 TO alex,finam;

COMMIT;
