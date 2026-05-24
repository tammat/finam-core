DROP VIEW IF EXISTS v_runtime_governance_dashboard CASCADE;

CREATE OR REPLACE VIEW v_runtime_governance_dashboard AS
SELECT
    rs.symbol,
    rs.strategy,
    rs.timeframe,

    rs.mode AS runtime_mode,
    rs.enabled AS runtime_enabled,

    rs.reason AS runtime_reason,

    er.event_status,
    er.allow_runtime AS event_allow_runtime,
    er.risk_multiplier,
    er.nearest_event_type,
    er.nearest_event_impact,
    er.reason AS event_reason,

    sp.session_bucket,
    sp.allow_runtime AS session_allow_runtime,
    sp.reason AS session_reason,

    CASE
        WHEN rs.enabled = FALSE THEN 'BLOCKED_RUNTIME'
        WHEN er.allow_runtime = FALSE THEN 'BLOCKED_EVENT'
        WHEN sp.allow_runtime = FALSE THEN 'BLOCKED_SESSION'
        ELSE 'ALLOWED'
    END AS governance_decision,

    CASE
        WHEN rs.enabled = FALSE THEN rs.reason
        WHEN er.allow_runtime = FALSE THEN er.reason
        WHEN sp.allow_runtime = FALSE THEN sp.reason
        ELSE 'runtime_разрешен'
    END AS governance_reason,

    now() AS calculated_at

FROM runtime_strategy_selection rs

LEFT JOIN strategy_event_risk_context er
    ON er.symbol = rs.symbol
   AND er.strategy = rs.strategy
   AND er.timeframe = rs.timeframe

LEFT JOIN session_runtime_policy sp
    ON sp.symbol = rs.symbol
   AND sp.strategy = rs.strategy
   AND sp.timeframe = rs.timeframe
   AND sp.session_bucket IN (
       'MOEX_MORNING',
       'MOEX_DAY',
       'US_OPEN_WINDOW',
       'MOEX_EVENING'
   );
