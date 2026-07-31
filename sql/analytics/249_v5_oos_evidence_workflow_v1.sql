BEGIN;

UPDATE analytics.system_job_schedule_v1
SET enabled=true,interval_minutes=5,updated_at=clock_timestamp()
WHERE job_code='TRADE_OUTCOME_OOS_ADMISSION'
  AND executor_code='TRADE_OUTCOME_OOS_ADMISSION_V1';

CREATE OR REPLACE VIEW analytics.v5_oos_evidence_panel_v1 AS
WITH paper AS (
    SELECT count(*)::int paper_trades,
           sum(net_pnl)::numeric paper_net_pnl,
           percentile_cont(0.5) WITHIN GROUP(ORDER BY net_pnl)::numeric paper_median_pnl,
           (sum(net_pnl) FILTER(WHERE net_pnl>0)
             / nullif(abs(sum(net_pnl) FILTER(WHERE net_pnl<0)),0))::numeric
             paper_profit_factor
    FROM public.closed_trades WHERE portfolio_scope LIKE 'FRESH_V5%'
), positive AS (
    SELECT greatest(sum(net_pnl) FILTER(WHERE net_pnl>0),0)::numeric gross_profit,
           greatest(max(net_pnl),0)::numeric best_trade
    FROM public.closed_trades WHERE portfolio_scope LIKE 'FRESH_V5%'
), symbols AS (
    SELECT max(symbol_profit)::numeric best_symbol
    FROM (
        SELECT symbol,greatest(sum(net_pnl),0) symbol_profit
        FROM public.closed_trades WHERE portfolio_scope LIKE 'FRESH_V5%'
        GROUP BY symbol
    ) grouped
), runs AS (
    SELECT count(*) FILTER(WHERE status_code='COLLECTING')::int collecting_runs,
           count(*) FILTER(WHERE status_code='OOS_PASS')::int passed_runs,
           count(*) FILTER(WHERE status_code='OOS_FAIL')::int failed_runs,
           coalesce(sum(observations_included),0)::int oos_included,
           coalesce(sum(observations_excluded),0)::int oos_excluded
    FROM analytics.v5_oos_run_v1
), admissions AS (
    SELECT count(*) FILTER(WHERE status_code='WAITING_FRESH_DATA')::int waiting_admissions,
           count(*) FILTER(WHERE status_code IN ('QUEUED','RUNNING'))::int frozen_admissions,
           coalesce(max(fresh_closed_trades) FILTER(WHERE status_code<>'CLOSED'),0)::int
             best_training_trades
    FROM analytics.trade_outcome_oos_admission_v1
), controls AS (
    SELECT avg(shadow_net_r) FILTER(WHERE shadow_entered)::numeric shadow_expectancy_r,
           avg(placebo_net_r)::numeric placebo_expectancy_r
    FROM analytics.entry_exit_signal_shadow_pair_v2
)
SELECT paper.*,runs.*,controls.*,
       CASE WHEN positive.gross_profit>0
            THEN positive.best_trade/positive.gross_profit ELSE 0 END top_trade_profit_share,
       CASE WHEN positive.gross_profit>0
            THEN symbols.best_symbol/positive.gross_profit ELSE 0 END top_symbol_profit_share,
       clock_timestamp() generated_at,
       admissions.*
FROM paper CROSS JOIN positive CROSS JOIN symbols CROSS JOIN runs
CROSS JOIN admissions CROSS JOIN controls;

GRANT SELECT ON analytics.v5_oos_evidence_panel_v1 TO alex,finam,finam_user;

COMMIT;
