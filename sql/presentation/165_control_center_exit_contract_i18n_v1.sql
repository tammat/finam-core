INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('column.scope.code','ru','Режим','Режим','Режим','Исследовательский горизонт: внутридневной или swing','','control_center_exit'),
('column.comparison.policy.code','ru','Сравнение','Сравнение','Сравн.','Базовое правило выхода для честного сравнения','','control_center_exit'),
('column.max.holding.bars','ru','Макс. баров','Макс.','Макс.','Предельное время удержания позиции в барах','','control_center_exit'),
('column.minimum.bars','ru','Мин. баров','Мин.','Мин.','Минимальное удержание до разрешения динамического выхода','','control_center_exit'),
('column.stop.atr','ru','Stop ATR','Stop','Stop','Расстояние защитного стопа в единицах ATR','','control_center_exit'),
('column.trail.atr','ru','Trail ATR','Trail','Trail','Расстояние плавающего стопа в единицах ATR','','control_center_exit'),
('column.trend.lookback','ru','Тренд, баров','Тренд','Тренд','Окно проверки исчезновения тренда','','control_center_exit'),
('column.evaluation.status','ru','Статус','Статус','Статус','Состояние фактической проверки правил выхода','','control_center_exit'),
('status.intraday','ru','Внутридневной','Внутри дня','Интрадей','Правила для внутридневных стратегий','','status'),
('status.swing','ru','Среднесрочный','Swing','Swing','Правила для среднесрочных стратегий','','status'),
('status.dynamic_exit_v1','ru','Динамический выход','Динамический','Динамич.','Выход по исчезновению тренда, росту риска, стопу или лимиту времени','','status'),
('status.fixed_hold','ru','Фиксированное удержание','Фиксированный','Фикс.','Базовый выход после фиксированного числа баров','','status'),
('status.awaiting_oos_exit_observations','ru','Ждёт OOS-сделок','Ждёт OOS','Ждёт','Правила настроены, но в текущей OOS-когорте ещё нет вариантов выхода','','status'),
('status.awaiting_closed_trades','ru','Ждёт закрытий','Ждёт закрытий','Ждёт','Варианты созданы, но закрытых сделок ещё нет','','status'),
('status.evaluated','ru','Проверено','Проверено','Готово','Есть закрытые сделки для оценки правил выхода','','status')
,
('status.trend_down','ru','Нисходящий тренд','Тренд вниз','Вниз','Рыночный режим с устойчивым нисходящим направлением','','status')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group;
