BEGIN;

INSERT INTO presentation.ui_resource_v1
    (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
    ('home.operator.status.measuring','ru','Измерение','Измерение','Замер','Система ожидает срок контрольного измерения.','','operator_decision_v2'),
    ('home.operator.status.measure_due','ru','Измерить','Измерить','Замер','Контрольное измерение доступно сейчас.','','operator_decision_v2'),
    ('home.operator.status.improved','ru','Улучшение','Улучшение','Плюс','Фактический результат улучшился относительно исходного значения.','','operator_decision_v2'),
    ('home.operator.status.no_effect','ru','Без эффекта','Без эффекта','Ноль','Фактический результат не изменился.','','operator_decision_v2'),
    ('home.operator.status.degraded','ru','Ухудшение','Ухудшение','Минус','Фактический результат ухудшился относительно исходного значения.','','operator_decision_v2'),
    ('home.operator.status.stale','ru','Устарело','Устарело','Архив','Источник больше не относится к активной воронке; результат сохранён для аудита.','','operator_decision_v2'),
    ('home.operator.next.measure','ru','Измерить результат','Измерить','Измерить','Двойной клик запускает контрольное измерение результата.','','operator_decision_v2'),
    ('home.operator.next.view','ru','Посмотреть результат','Результат','Итог','Двойной клик показывает фактический результат и исходные данные.','','operator_decision_v2')
    ,('column.operator.deadline','ru','Время','Время','Время','Срок действия либо время получения фактического результата.','','column')
ON CONFLICT (resource_key,locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
    resource_group=EXCLUDED.resource_group;

COMMIT;
