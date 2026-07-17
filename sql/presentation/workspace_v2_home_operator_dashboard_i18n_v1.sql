INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('home.operator.section.title','ru','Операторская панель','Оператор','Опер.','Ключевые рабочие контуры оператора','', 'workspace_v2_home_operator'),
('home.operator.section.subtitle','ru','События, риски, рекомендации и здоровье модели','Контуры','Конт.','Сводка оператора без перехода в терминал','', 'workspace_v2_home_operator'),

('home.operator.model_health.title','ru','Здоровье модели','Model Health','Здор.','Состояние компонентов модели','', 'workspace_v2_home_operator'),
('home.operator.model_health.subtitle','ru','Контроль качества модели','Качество','Кач.','Снимки и рекомендации model health','', 'workspace_v2_home_operator'),

('home.operator.recommendations.title','ru','Рекомендации','Рекомендации','Рек.','Очередь рекомендаций и оценок','', 'workspace_v2_home_operator'),
('home.operator.recommendations.subtitle','ru','Что требует внимания','Внимание','Вним.','Рекомендации системы','', 'workspace_v2_home_operator'),

('home.operator.edge_search.title','ru','Поиск edge','Поиск edge','Edge','Автоматический поиск подтверждённого преимущества','', 'workspace_v2_home_operator'),
('home.operator.edge_search.subtitle','ru','Проверка алгоритмов и рынков','Алгоритмы','Алг.','Текущий цикл поиска и вневыборочной проверки','', 'workspace_v2_home_operator'),
('home.operator.edge_search.summary','ru','{status} · {progress}% · вариантов {variants} · PASS {passes} · {algorithms}','{progress}% · PASS {passes} · {algorithms}','{progress}% · PASS {passes}','Статус, прогресс, варианты и подтверждённые результаты','', 'workspace_v2_home_operator'),

('home.operator.signal_funnel.title','ru','Воронка сигналов','Воронка','Ворон.','Стадии прохождения сигналов','', 'workspace_v2_home_operator'),
('home.operator.signal_funnel.subtitle','ru','Где теряются возможности','Потери','Пот.','Аналитика причин блокировок','', 'workspace_v2_home_operator'),

('home.operator.risk.title','ru','Риск','Риск','Риск','Риск-события и решения','', 'workspace_v2_home_operator'),
('home.operator.risk.subtitle','ru','Контроль ограничений','Ограничения','Огр.','Решения Risk Engine','', 'workspace_v2_home_operator'),

('home.operator.events.title','ru','События','События','Соб.','Событийный журнал системы','', 'workspace_v2_home_operator'),
('home.operator.events.subtitle','ru','Последние системные события','Журнал','Жур.','События исполнения и системы','', 'workspace_v2_home_operator')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group;
