INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('portfolio.workspace.title','ru','Портфель','Портфель','Портф.','Рабочее место портфеля','', 'workspace_v2_portfolio'),
('portfolio.workspace.subtitle','ru','Капитал, позиции и риск','Капитал и позиции','Капитал','Сводка портфеля без изменения заявок и исполнения','', 'workspace_v2_portfolio'),

('portfolio.section.summary.title','ru','Сводка','Сводка','Свод.','Ключевые показатели портфеля','', 'workspace_v2_portfolio'),
('portfolio.section.summary.subtitle','ru','Общее состояние портфеля','Состояние','Сост.','Агрегированная информация по портфелю','', 'workspace_v2_portfolio'),
('portfolio.section.summary.tooltip','ru','Сводная информация портфеля','Сводка портфеля','Сводка','Источник: готовые представления портфеля','', 'workspace_v2_portfolio'),

('portfolio.section.positions.title','ru','Позиции','Позиции','Поз.','Открытые и учтенные позиции','', 'workspace_v2_portfolio'),
('portfolio.section.positions.subtitle','ru','Состав портфеля','Состав','Сост.','Позиции по инструментам','', 'workspace_v2_portfolio'),
('portfolio.section.positions.tooltip','ru','Позиции портфеля','Позиции','Поз.','Источник: представление позиций','', 'workspace_v2_portfolio'),

('portfolio.section.dashboard.title','ru','Панель позиций','Панель','Пан.','Показатели для панели позиций','', 'workspace_v2_portfolio'),
('portfolio.section.dashboard.subtitle','ru','Контроль позиций','Контроль','Контр.','Рабочие показатели контроля позиций','', 'workspace_v2_portfolio'),
('portfolio.section.dashboard.tooltip','ru','Панель контроля позиций','Панель','Пан.','Источник: dashboard-представление','', 'workspace_v2_portfolio'),

('portfolio.section.visualization.title','ru','Визуализация','Визуализация','Виз.','Данные для визуализации портфеля','', 'workspace_v2_portfolio'),
('portfolio.section.visualization.subtitle','ru','Структура портфеля','Структура','Структ.','Визуальная структура портфеля','', 'workspace_v2_portfolio'),
('portfolio.section.visualization.tooltip','ru','Визуализация портфеля','Визуализация','Виз.','Источник: visualization-представление','', 'workspace_v2_portfolio'),

('portfolio.source.public_v_real_portfolio_summary_ru','ru','Сводка портфеля','Сводка','Свод.','Источник: v_real_portfolio_summary_ru','', 'workspace_v2_portfolio'),
('portfolio.source.public_v_real_portfolio_positions_ru','ru','Позиции портфеля','Позиции','Поз.','Источник: v_real_portfolio_positions_ru','', 'workspace_v2_portfolio'),
('portfolio.source.public_v_positions_dashboard_ru','ru','Панель позиций','Панель','Пан.','Источник: v_positions_dashboard_ru','', 'workspace_v2_portfolio'),
('portfolio.source.public_v_portfolio_visualization_ru','ru','Структура портфеля','Структура','Структ.','Источник: v_portfolio_visualization_ru','', 'workspace_v2_portfolio'),

('portfolio.card.subtitle','ru','Данные портфеля','Данные','Дан.','Карточка данных портфеля','', 'workspace_v2_portfolio'),
('portfolio.card.tooltip','ru','Данные из портфельного представления','Данные','Дан.','Данные только для чтения','', 'workspace_v2_portfolio'),

('ui.status.ok','ru','ОК','ОК','ОК','Проверка пройдена','', 'ui_status'),
('ui.status.warning','ru','Требует внимания','Внимание','Вним.','Есть ограничения или недостаточно данных','', 'ui_status'),
('ui.action.open','ru','Открыть','Открыть','Откр.','Открыть раздел','', 'ui_action')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group;
