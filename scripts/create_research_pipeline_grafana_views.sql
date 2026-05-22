CREATE OR REPLACE VIEW v_research_pipeline_runs_grafana AS
SELECT
    id AS "ID запуска",
    started_at AS "Начало",
    finished_at AS "Окончание",
    ROUND(EXTRACT(EPOCH FROM (finished_at - started_at))::numeric, 3) AS "Длительность, сек",
    trade_source AS "Источник сделок",
    symbols_total AS "Символов всего",
    symbols_ok AS "Символов успешно",
    symbols_failed AS "Символов с ошибкой",
    status AS "Статус",
    error_message AS "Ошибка"
FROM research_pipeline_runs
ORDER BY id DESC;


CREATE OR REPLACE VIEW v_research_pipeline_steps_grafana AS
SELECT
    id AS "ID шага",
    run_id AS "ID запуска",
    symbol AS "Инструмент",
    step_name AS "Шаг",
    started_at AS "Начало",
    finished_at AS "Окончание",
    duration_sec AS "Длительность, сек",
    status AS "Статус",
    return_code AS "Код возврата",
    error_message AS "Ошибка",
    command AS "Команда"
FROM research_pipeline_step_events
ORDER BY id DESC;


CREATE OR REPLACE VIEW v_strategy_lifecycle_grafana AS
SELECT
    symbol AS "Инструмент",
    strategy AS "Стратегия",
    timeframe AS "Таймфрейм",
    lifecycle_state AS "Состояние",
    allow_runtime AS "Разрешён runtime",
    allow_radar AS "Разрешён radar",
    allow_research AS "Разрешён research",
    reason AS "Причина",
    updated_at AS "Обновлено"
FROM strategy_lifecycle_state
ORDER BY updated_at DESC;


CREATE OR REPLACE VIEW v_strategy_promotion_decisions_grafana AS
SELECT
    symbol AS "Инструмент",
    strategy AS "Стратегия",
    timeframe AS "Таймфрейм",
    trade_source AS "Источник сделок",
    decision AS "Решение",
    target_lifecycle_state AS "Целевое состояние",
    allow_runtime AS "Разрешён runtime",
    allow_radar AS "Разрешён radar",
    allow_research AS "Разрешён research",
    reason AS "Причина",
    decided_at AS "Время решения"
FROM strategy_promotion_decisions
ORDER BY decided_at DESC;


CREATE OR REPLACE VIEW v_trade_fill_quality_audit_grafana AS
SELECT
    symbol AS "Инструмент",
    trade_source AS "Источник сделок",
    total_fills AS "Всего fill",
    buy_fills AS "BUY fill",
    sell_fills AS "SELL fill",
    missing_strategy AS "Без стратегии",
    missing_timeframe AS "Без таймфрейма",
    backfill_fills AS "Backfill fill",
    status AS "Статус качества",
    reconstruction_allowed AS "Реконструкция разрешена",
    reason AS "Причина",
    calculated_at AS "Рассчитано"
FROM trade_fill_quality_audit
ORDER BY calculated_at DESC;
