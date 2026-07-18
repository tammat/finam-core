BEGIN;
CREATE TABLE IF NOT EXISTS analytics.edge_research_universe_override_v1 (
    symbol TEXT PRIMARY KEY,
    inclusion_mode TEXT CHECK (inclusion_mode IN ('FORCE_INCLUDE','FORCE_EXCLUDE')),
    priority_override INTEGER CHECK (priority_override BETWEEN 1 AND 100),
    active BOOLEAN NOT NULL DEFAULT true,
    request_id UUID NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (inclusion_mode IS NOT NULL OR priority_override IS NOT NULL)
);
GRANT SELECT,INSERT,UPDATE ON analytics.edge_research_universe_override_v1 TO alex;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.universe.reason.operator_force_included','ru','Включён оператором','Включён','Включён','Применяется со следующего цикла','','research'),
('research.universe.reason.operator_force_excluded','ru','Исключён оператором','Исключён','Исключён','Применяется со следующего цикла','','research'),
('research.universe.reason.operator_priority_selected','ru','Приоритет оператора','Приоритет','Приор.','Выбран с учётом заданного приоритета','','research')
,('research.domain.completed','ru','Выполнено','Выполнено','Готово','Процесс завершён системой','','research')
,('research.domain.completed.tooltip','ru','Системный процесс успешно завершён','Процесс завершён','Готово','Финальный статус процесса','','research')
,('research.domain.worker_command_failed.research_refresh.1','ru','Ошибка обновления исследований','Ошибка обновления','Ошибка','Системное обновление завершилось с ошибкой','','research')
,('research.domain.worker_command_failed.research_refresh.1.tooltip','ru','Исполнитель обновления исследований вернул ошибку','Ошибка исполнителя','Ошибка','Система сохранит ошибку и повторит процесс по расписанию','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,resource_group=EXCLUDED.resource_group;
COMMIT;
