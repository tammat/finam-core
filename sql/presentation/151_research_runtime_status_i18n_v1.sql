BEGIN;

INSERT INTO presentation.ui_resource_v1
    (resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, resource_group, source_version)
VALUES
    ('research.domain.cancelled', 'ru', 'Отменено', 'Отменено', 'Отменено', 'Заявка отменена', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.cancelled.tooltip', 'ru', 'Заявка отменена системой или оператором', 'Отменено', 'Отменено', 'Заявка отменена системой или оператором', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.command_cancelled', 'ru', 'Команда отменена', 'Отменена', 'Отменена', 'Выполнение команды отменено', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.command_cancelled.tooltip', 'ru', 'Выполнение команды отменено', 'Отменена', 'Отменена', 'Выполнение команды отменено', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.edge_regime_discovery_checkpointed', 'ru', 'Режимы сохранены', 'Сохранено', 'Сохранено', 'Определение режимов продолжится с контрольной точки', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.edge_regime_discovery_checkpointed.tooltip', 'ru', 'Определение режимов продолжится с контрольной точки', 'Сохранено', 'Сохранено', 'Определение режимов продолжится с контрольной точки', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.walkforward_checkpointed', 'ru', 'Фолды сохранены', 'Сохранено', 'Сохранено', 'Walk-forward продолжится с контрольной точки', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.walkforward_checkpointed.tooltip', 'ru', 'Walk-forward продолжится с контрольной точки', 'Сохранено', 'Сохранено', 'Walk-forward продолжится с контрольной точки', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.enqueued.tooltip', 'ru', 'Заявка поставлена в системную очередь', 'В очереди', 'Очередь', 'Заявка поставлена в системную очередь', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1'),
    ('research.domain.waiting.tooltip', 'ru', 'Процесс ожидает данных или разрешённого окна', 'Ожидает', 'Ожидает', 'Процесс ожидает данных или разрешённого окна', 'research', 'RESEARCH_RUNTIME_STATUS_I18N_V1')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
    caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    resource_group = EXCLUDED.resource_group,
    source_version = EXCLUDED.source_version,
    updated_at = clock_timestamp();

COMMIT;
