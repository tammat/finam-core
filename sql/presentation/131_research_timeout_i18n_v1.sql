INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.domain.edge_search_step_timeout.discover_regime','ru',
 'Тайм-аут определения режима','Тайм-аут режима','Тайм-аут',
 'Этап определения рыночного режима не завершился в отведённое время. Система повторит его по расписанию.','','research'),
('research.domain.edge_search_step_timeout.discover_regime.tooltip','ru',
 'Этап определения рыночного режима не завершился в отведённое время. Система повторит его по расписанию.',
 'Повтор по расписанию','Повтор',
 'Этап определения рыночного режима не завершился в отведённое время. Система повторит его по расписанию.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
