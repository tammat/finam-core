BEGIN;

INSERT INTO presentation.ui_resource_v1
    (resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
    ('column.operator.task', 'ru', 'Задача', 'Задача', 'Задача', 'Что требуется выполнить.', '', 'column'),
    ('home.operator.status.accepted', 'ru', 'Принято', 'Принято', 'Принято', 'Рекомендация принята оператором к рассмотрению.', '', 'operator_decision_v2'),
    ('home.operator.status.expired', 'ru', 'Просрочено', 'Просрочено', 'Просрочено', 'Срок действия рекомендации истёк.', '', 'operator_decision_v2'),
    ('home.operator.status.blocked', 'ru', 'Блок', 'Блок', 'Блок', 'Выполнение заблокировано политикой допуска.', '', 'operator_decision_v2'),
    ('home.operator.status.done', 'ru', 'Готово', 'Готово', 'Готово', 'Рекомендованное действие выполнено.', '', 'operator_decision_v2'),
    ('home.operator.status.waiting', 'ru', 'Ожидает', 'Ожидает', 'Ожидает', 'Система ожидает подтверждение или новые данные.', '', 'operator_decision_v2'),
    ('home.operator.status.decision', 'ru', 'Решение', 'Решение', 'Решение', 'Требуется решение оператора.', '', 'operator_decision_v2')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
    caption = EXCLUDED.caption,
    caption_short = EXCLUDED.caption_short,
    caption_mobile = EXCLUDED.caption_mobile,
    tooltip = EXCLUDED.tooltip,
    resource_group = EXCLUDED.resource_group;

COMMIT;
