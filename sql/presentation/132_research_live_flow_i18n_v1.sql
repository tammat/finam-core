BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.live_signals','ru','Сигналы за час','Сигналы','Сигн.','Новые сигналы системы за последний час','','research'),
('research.tile.paper_fills','ru','Paper-сделки за час','Paper-сделки','Сделки','Модельные исполнения за последний час; реальные заявки не создаются','','research'),
('research.tile.closed_trades','ru','Закрыто за час','Закрыто','Закр.','Закрытые сделки, уже пригодные для оценки результата','','research'),
('research.tile.regime_progress','ru','Поиск режимов, %','Режимы, %','Режимы','Доля завершённых DB-задач этапа определения рыночных режимов','','research'),
('research.current.regime_tasks','ru','Задачи режимов','Задачи','Задачи','Завершённые и все задачи текущей кампании','','research'),
('research.current.regime_tasks.value','ru','{completed} из {total}','{completed}/{total}','{completed}/{total}','Завершено {completed} задач из {total}','','research'),
('research.current.regime_progress','ru','Прогресс режимов, %','Режимы, %','Режимы','Сохранённый прогресс DISCOVER_REGIME в PostgreSQL','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
 caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
 icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

COMMIT;
