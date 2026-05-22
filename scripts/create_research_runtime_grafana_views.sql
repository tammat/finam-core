CREATE OR REPLACE VIEW v_research_runtime_state_grafana AS
SELECT
    supervisor_name AS "Supervisor",
    status AS "Статус",
    active_symbols AS "Активные инструменты",
    failed_symbols AS "Проблемные инструменты",
    last_error AS "Последняя ошибка",
    last_cycle_at AS "Последний цикл",
    last_success_at AS "Последний успешный цикл",
    updated_at AS "Обновлено"
FROM research_runtime_state
ORDER BY updated_at DESC;


CREATE OR REPLACE VIEW v_research_runtime_cycle_log_grafana AS
SELECT
    id AS "ID цикла",
    supervisor_name AS "Supervisor",
    symbols AS "Инструменты",
    trade_source AS "Источник сделок",
    started_at AS "Начало",
    finished_at AS "Окончание",
    duration_sec AS "Длительность, сек",
    status AS "Статус",
    return_code AS "Код возврата",
    error_message AS "Ошибка"
FROM research_runtime_cycle_log
ORDER BY id DESC;
