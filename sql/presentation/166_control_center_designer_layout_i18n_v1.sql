INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('control.view.group.process.description','ru','Что выполняется сейчас, что завершено и какой шаг будет следующим','Циклы и очередь','Циклы','Системные циклы, очередь, прогресс и результаты выполнения','','control_center_view'),
('control.view.group.funnel.description','ru','Где кандидаты проходят проверку и на каком этапе теряется преимущество','Переходы и потери','Потери','Переходы, конверсии и причины потерь между стадиями','','control_center_view'),
('control.view.group.execution.description','ru','Свежесть котировок, покрытие стаканом и готовность модельного исполнения','Данные и сделки','Исполнение','Котировки, bid/ask, глубина стакана и модельные сделки','','control_center_view'),
('control.view.group.methodology.description','ru','Условия входа и выхода, риск, устойчивость и блокирующие ограничения','Правила и риск','Правила','Статистика, устойчивость, входы, выходы, риск и ограничения','','control_center_view'),
('control.view.group.count','ru','{sections} разделов · {blocked} ограничений','{sections} · ограничений {blocked}','{sections}/{blocked}','Число разделов и блокирующих ограничений','','control_center_view')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
