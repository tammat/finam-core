BEGIN;
INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.universe.column.status','ru','Статус','Статус','Статус','Состояние последнего действия по инструменту','','research'),
('research.domain.not_requested','ru','Нет заявки','Нет заявки','Нет','Действия для следующего цикла не запрашивались','','research'),
('research.domain.not_requested.tooltip','ru','Для инструмента нет заявки оператора','Нет заявки','Нет','Действует автоматический выбор системы','','research')
,('research.domain.apply_to_next_research_cycle','ru','Применить в следующем цикле','Следующий цикл','След. цикл','Изменение не затрагивает текущий цикл','','research')
,('research.domain.apply_to_next_research_cycle.tooltip','ru','Заявка будет учтена при формировании следующего исследовательского цикла','Следующий цикл','След. цикл','Текущий выполняющийся цикл остаётся неизменным','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,resource_group=EXCLUDED.resource_group;
COMMIT;
