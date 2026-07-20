BEGIN;

INSERT INTO presentation.ui_resource_v1
    (resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, resource_group, source_version)
VALUES
    ('status.walkforward_checkpointed', 'ru', 'Walk-forward сохранён', 'Сохранён', 'Сохранён',
     'Результаты фолдов сохранены; расчёт продолжится с контрольной точки', 'status', 'CONTROL_CENTER_STATUS_I18N_V1'),
    ('status.continue_on_next_system_schedule', 'ru', 'Продолжить по расписанию', 'По расписанию', 'Расписание',
     'Система продолжит процесс в следующее разрешённое окно', 'status', 'CONTROL_CENTER_STATUS_I18N_V1')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
    caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    resource_group = EXCLUDED.resource_group,
    source_version = EXCLUDED.source_version,
    updated_at = clock_timestamp();

COMMIT;
