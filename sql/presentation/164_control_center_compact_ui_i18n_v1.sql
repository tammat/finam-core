INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('status.europe_overlap','ru','Пересечение с европейской сессией','Европа','Европа','Активны Московская и европейская торговые сессии','','status'),
('status.outside_session','ru','Вне торговой сессии','Вне сессии','Закрыто','Торговая сессия закрыта','','status'),
('status.volatility_scaled_momentum_v1','ru','Импульс с поправкой на волатильность','Вол.-импульс','Импульс','Импульс нормализован на текущую волатильность','','status'),
('status.ema_trend_filter_v1','ru','Трендовый фильтр EMA','EMA-тренд','EMA','Условия входа подтверждаются направлением EMA','','status'),
('status.quote_matched','ru','Сделка сопоставлена со стаканом','Стакан найден','Сопоставлено','Для сделки найдены реальные bid/ask и снимок стакана','','status')
,
('control.view.group.process','ru','Процессы','Процессы','Процессы','Системные циклы, очередь и результаты выполнения','','control_center_view'),
('control.view.group.funnel','ru','Воронка','Воронка','Воронка','Переходы и потери между стадиями проверки','','control_center_view'),
('control.view.group.execution','ru','Исполнение','Исполнение','Исполнение','Котировки, стакан, сделки и требования к исполнению','','control_center_view'),
('control.view.group.methodology','ru','Методология','Методология','Методология','Статистика, устойчивость, риск и связи','','control_center_view'),
('control.view.group.count','ru','{sections} разделов · блоков {blocked}','{sections} · блоков {blocked}','{sections}/{blocked}','Число разделов и блокирующих состояний','','control_center_view'),
('control.view.toolbar.aria','ru','Управление подробностями','Вид','Вид','Выбор уровня детализации контрольной панели','','control_center_view'),
('control.view.summary','ru','Главное','Главное','Главное','Скрыть подробные разделы и оставить сводку','','control_center_view'),
('control.view.blocked','ru','Только блоки','Блоки','Блоки','Показать только разделы с блокирующими состояниями','','control_center_view'),
('control.view.all','ru','Все детали','Все','Все','Открыть все подробные разделы','','control_center_view')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
