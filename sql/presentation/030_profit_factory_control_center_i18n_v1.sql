INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('home.profit_factory.title','ru','Центр управления прибылью','Прибыль','Прибыль','Главные показатели Profit Factory','◎','profit_factory_control_center'),
('home.profit_factory.subtitle','ru','Решение оператора на основе подтверждённых финансовых данных','Решение и KPI','Решение','Только данные, прошедшие Trust Gate','','profit_factory_control_center'),
('home.profit_factory.decision','ru','Рекомендуемое действие','Действие','Действие','Главное решение оператора','','profit_factory_control_center'),
('home.profit_factory.expected','ru','Ожидаемая прибыль','Ожидание','Ожид.','Ожидаемая прибыль за период','','profit_factory_control_center'),
('home.profit_factory.realized','ru','Реализованная прибыль','Факт','Факт','Фактически реализованная прибыль','','profit_factory_control_center'),
('home.profit_factory.gap','ru','Разрыв до цели','Разрыв','Разрыв','Ожидаемая прибыль минус реализованная','','profit_factory_control_center'),
('home.profit_factory.roi','ru','Фактический ROI','ROI','ROI','Реализованная прибыль к выделенному капиталу','','profit_factory_control_center'),
('home.profit_factory.verified','ru','Только проверенные данные','Проверено','Проверено','Trust Gate обязателен','','profit_factory_control_center'),
('home.profit_factory.quality','ru','Качество данных','Качество','Кач.','Статус доверия к данным','','profit_factory_control_center')
,
('home.card.profit.title','ru','Прибыль','Прибыль','Прибыль','Центр управления прибылью и решениями','◎','profit_factory_control_center')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption, caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile, tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon, resource_group=EXCLUDED.resource_group, updated_at=now();
