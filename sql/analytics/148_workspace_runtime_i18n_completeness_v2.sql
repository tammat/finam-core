BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.domain.research.tooltip','ru','Исследовательский процесс','Исследование','Исслед.','Состояние автономного поиска торгового преимущества','','research'),
('workspace.loading','ru','Открываю раздел…','Загрузка…','Загрузка…','Раздел загружается','','workspace'),
('research.domain.quotes.tooltip','ru','Поток и свежесть рыночных котировок','Котировки','Котир.','Состояние входных рыночных данных для исследования','','research'),
('status.checkpointed','ru','Сохранена контрольная точка','Сохранено','Сохран.','Процесс продолжится с сохранённой контрольной точки','','status'),
('status.edge_regime_discovery_checkpointed','ru','Поиск режимов сохранён','Режим сохранён','Сохран.','Определение рыночного режима продолжится с контрольной точки','','status'),
('status.skipped','ru','Пропущено по плану','Пропущено','Пропуск','Этап пропущен согласно системному плану','','status'),
('status.rejection_reason_or_status','ru','Причина отказа или статус','Причина','Причина','Причина, по которой сигнал не дошёл до заявки','','status'),
('status.cluster_block:energy','ru','Блокировка группы энергетических инструментов','Блок группы','Блок','Ограничение одновременных позиций в энергетической группе','','status'),
('status.runtime_strategy_blocked:стратегия_заблокирована_по_статистике','ru','Стратегия заблокирована по статистике','Стат. блок','Блок','Свежая статистика стратегии не разрешает исполнение','','status'),
('status.trend_flip_block','ru','Блокировка при смене тренда','Смена тренда','Блок','Сигнал отклонён из-за смены направления тренда','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
