CREATE OR REPLACE VIEW grafana_portfolio_governance AS
SELECT
    created_at                                      AS "Время",
    symbol                                          AS "Инструмент",
    strategy                                        AS "Стратегия",

    CASE portfolio_heat_status
        WHEN 'LOW' THEN '🟢 Низкий'
        WHEN 'MEDIUM' THEN '🟡 Средний'
        WHEN 'HIGH' THEN '🟠 Высокий'
        WHEN 'EXTREME' THEN '🔴 Критический'
        ELSE portfolio_heat_status
    END                                             AS "Перегрев портфеля",

    portfolio_risk_multiplier                       AS "Множитель риска",

    COALESCE(exit_policy, 'не задана')              AS "Политика выхода",

    CASE
        WHEN allow_new_entries THEN '✅ Разрешены'
        ELSE '⛔ Заблокированы'
    END                                             AS "Новые входы",

    CASE governance_mode
        WHEN 'ADVISORY_ONLY'
            THEN '📘 Advisory'
        ELSE governance_mode
    END                                             AS "Режим governance"

FROM portfolio_governance_events
ORDER BY created_at DESC;
