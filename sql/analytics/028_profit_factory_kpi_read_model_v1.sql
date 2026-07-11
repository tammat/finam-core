CREATE OR REPLACE VIEW analytics.profit_factory_kpi_candidate_v1 AS
SELECT
    i.candidate_id,
    i.strategy_code,
    i.symbol,
    i.timeframe,
    i.data_scope,
    t.data_quality_status,
    t.financial_kpi_eligible,
    a.allocation_id,
    a.allocation_status,
    a.capital_allocated,
    f.currency_code,
    f.expected_profit,
    f.realized_profit,
    f.expected_profit - f.realized_profit AS profit_gap,
    CASE WHEN a.capital_allocated=0 THEN 0
         ELSE f.expected_profit/a.capital_allocated END AS expected_roi,
    CASE WHEN a.capital_allocated=0 THEN 0
         ELSE f.realized_profit/a.capital_allocated END AS realized_roi,
    f.measurement_from,
    f.measurement_to,
    f.created_at AS refreshed_at
FROM analytics.profit_factory_candidate_identity_v1 i
JOIN analytics.profit_factory_trust_status_v1 t USING(candidate_id)
JOIN analytics.profit_factory_production_allocation_v1 a USING(candidate_id)
JOIN analytics.profit_factory_profit_fact_v1 f USING(candidate_id, allocation_id)
WHERE t.financial_kpi_eligible
  AND i.data_scope=a.data_scope
  AND i.data_scope=f.data_scope;

CREATE OR REPLACE VIEW analytics.profit_factory_kpi_summary_v1 AS
SELECT
    data_scope,
    count(DISTINCT candidate_id) AS eligible_candidates,
    sum(capital_allocated) AS capital_allocated,
    sum(expected_profit) AS expected_profit,
    sum(realized_profit) AS realized_profit,
    sum(profit_gap) AS profit_gap,
    CASE WHEN sum(capital_allocated)=0 THEN 0
         ELSE sum(expected_profit)/sum(capital_allocated) END AS expected_roi,
    CASE WHEN sum(capital_allocated)=0 THEN 0
         ELSE sum(realized_profit)/sum(capital_allocated) END AS realized_roi,
    max(refreshed_at) AS refreshed_at
FROM analytics.profit_factory_kpi_candidate_v1
GROUP BY data_scope;

GRANT SELECT ON analytics.profit_factory_kpi_candidate_v1 TO alex;
GRANT SELECT ON analytics.profit_factory_kpi_summary_v1 TO alex;
