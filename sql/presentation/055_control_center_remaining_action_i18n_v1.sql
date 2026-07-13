INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.market.title','ru','Рыночные предпосылки','Предпосылки','Рынок','','','research'),
('research.market.subtitle','ru','Свежесть, история и покрытие режимами по каждому инструменту','Качество рыночных данных','Качество','','','research'),
('research.exit.title','ru','Политика выхода и время удержания','Выход и удержание','Выход','','','research'),
('research.exit.subtitle','ru','Сравнение только новых Shadow-наблюдений без брокерских заявок','Shadow-варианты выхода','Shadow','','','research'),
('research.block.title','ru','Блокирующие ограничения','Блокировки','Блокировки','','','research'),
('research.block.subtitle','ru','Подтверждённые причины; снятие блокировки требует отдельного подтверждения оператора','Только подтверждённые причины','Причины','','','research'),
('research.solution.use_ready','ru','Источник готов: использовать в следующем forward-наблюдении','Использовать','Готово','','','research'),
('research.solution.refresh_data','ru','Обновить историю и повторить quality gate','Обновить данные','Обновить','','','research'),
('research.solution.observe_exit','ru','Продолжить Shadow до закрытых наблюдений','Продолжить Shadow','Наблюдать','','','research'),
('research.solution.compare_exit','ru','Сравнить net PnL и удержание с базовой policy','Сравнить с базовой','Сравнить','','','research'),
('research.solution.keep_blocked','ru','Оставить блокировку до устранения подтверждённой причины','Оставить блокировку','Блокировать','','','research'),
('column.bars','ru','Бары','Бары','Бары','','','column'),('column.days','ru','Дни','Дни','Дни','','','column'),
('column.age','ru','Возраст','Возраст','Возраст','','','column'),('column.policy','ru','Policy','Policy','Policy','','','column'),
('column.closed','ru','Закрыты','Закрыты','Закр.','','','column'),('column.hold_minutes','ru','Удержание, мин','Минуты','Мин.','','','column'),
('column.net_pnl','ru','Net PnL','Net PnL','PnL','','','column'),('column.trailing_exits','ru','Трейлинг','Трейлинг','Трейл.','','','column'),
('column.source','ru','Источник','Источник','Источник','','','column')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

UPDATE presentation.control_center_recommendation_route_v1 SET action_target=CASE reason_group
 WHEN 'UNKNOWN' THEN '/workspace-v2/control-center/edge-oos#market-prerequisites'
 WHEN 'EXIT' THEN '/workspace-v2/control-center/edge-oos#exit-analysis'
 WHEN 'BLOCK' THEN '/workspace-v2/control-center/edge-oos#block-analysis' ELSE action_target END,
 source_version='CONTROL_CENTER_REMAINING_ACTION_V1',updated_at=now()
WHERE reason_group IN('UNKNOWN','EXIT','BLOCK');
