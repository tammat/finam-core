BEGIN;
INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.domain.selected.tooltip','ru','Включён в текущий исследовательский цикл','Включён','В цикле','Почему инструмент включён в цикл','','research'),
('research.domain.excluded.tooltip','ru','Не включён в текущий исследовательский цикл','Исключён','Вне цикла','Почему инструмент не включён в цикл','','research'),
('research.domain.skipped','ru','Пропущено','Пропуск','Проп.','Этап не выполнялся','','research'),
('research.domain.skipped.tooltip','ru','Этап пропущен согласно системному плану','Этап пропущен','Пропущено','Причина пропуска сохранена в системном цикле','','research'),
('research.domain.edge_search_executor_failed.methodology_gate','ru','Сбой методологической проверки','Сбой проверки','Сбой','Исполнитель не завершил методологическую проверку','','research'),
('research.domain.edge_search_executor_failed.methodology_gate.tooltip','ru','Системный исполнитель завершился с ошибкой на методологической проверке','Ошибка исполнителя','Ошибка','Повтор будет создан системным планировщиком','','research'),
('research.domain.edge_search_server_load_high','ru','Высокая нагрузка сервера','Высокая нагрузка','Нагрузка','Запуск отложен из-за нагрузки','','research'),
('research.domain.edge_search_server_load_high.tooltip','ru','Новый цикл отложен до разрешённого окна нагрузки','Ожидает окна','Ожидание','Система повторит запуск автоматически','','research'),
('research.domain.donchian_trend_expansion.tooltip','ru','Пробой канала Дончиана по направлению тренда','Пробой Дончиана','Дончиан','Алгоритм расширения трендового диапазона','','research'),
('research.domain.intermarket_sber_spread.tooltip','ru','Межрыночное отклонение обыкновенных и привилегированных акций Сбербанка','Спред Сбербанка','Спред','Алгоритм межрыночного спреда','','research'),
('research.domain.relative_strength.tooltip','ru','Относительная сила инструмента к рынку','Относительная сила','Сила','Алгоритм относительной силы','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
COMMIT;
