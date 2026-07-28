BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('workspace.drawer.functions','ru','Рабочий стол','Рабочий стол','Функции','Основные функции оператора','','workspace'),
('workspace.menu.home','ru','Главная','Главная','Главная','Открыть главную страницу','','workspace'),
('workspace.menu.research','ru','Исследования','Исследования','Поиск','Поиск и проверка торгового преимущества','','workspace'),
('workspace.menu.control','ru','Контрольный центр','Контроль','Контроль','Воронки, допуски и методология','','workspace'),
('workspace.menu.intraday','ru','Торговля','Торговля','Торговля','Модельные, теневые и реальные сделки','','workspace'),
('workspace.menu.portfolio','ru','Портфель','Портфель','Портфель','Позиции и портфельные ограничения','','workspace'),
('workspace.menu.risk','ru','Риск','Риск','Риск','Риск-контур и лимиты','','workspace'),
('workspace.menu.capital','ru','Капитал','Капитал','Капитал','Прибыль и системное масштабирование капитала','','workspace'),
('workspace.menu.system','ru','Система','Система','Система','Состояние служб и события','','workspace'),
('workspace.menu.settings','ru','Настройки','Настройки','Настройки','Настройки рабочего пространства','','workspace')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=excluded.caption,caption_short=excluded.caption_short,
caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
