INSERT INTO presentation.ui_resource_v1 (
    resource_key,locale_code,caption,caption_short,caption_mobile,
    tooltip,icon,resource_group
) VALUES
('research.volatility.title','ru','Результаты по режимам волатильности','Волатильность','Волатильность','','','research'),
('research.volatility.subtitle','ru','Сравнение OOS без смешивания рыночных режимов','Сравнение OOS','Сравнение','','','research'),
('research.risk.title','ru','Лимиты риска и размер позиции','Риск и позиция','Риск','','','research'),
('research.risk.subtitle','ru','Фактические решения versioned risk policy; изменение лимитов здесь не выполняется','Только решения policy','Policy','','','research'),
('research.entry.title','ru','Условия входа и варианты параметров','Условия входа','Вход','','','research'),
('research.entry.subtitle','ru','Параметры из OOS; продвижение только при подтверждённом PASS','Только подтверждённые параметры','OOS','','','research'),
('research.execution.title','ru','Издержки и качество исполнения','Качество исполнения','Исполнение','','','research'),
('research.execution.subtitle','ru','Фактические Paper и Shadow fills; bid/ask и стакан не подменяются OHLCV','Фактические исполнения','Исполнения','','','research'),
('research.recommendation.confirm_title','ru','Выберите вариант решения','Выберите вариант','Вариант','','','research'),
('research.recommendation.confirm','ru','Подтвердить выбор','Подтвердить','Подтвердить','','','research'),
('research.solution.promote','ru','Кандидат подтверждён: передать в Shadow-наблюдение','Передать в Shadow','В Shadow','','','research'),
('research.solution.collect_evidence','ru','Недостаточно доказательств: увеличить forward/OOS выборку без изменения финального holdout','Собрать доказательства','Наблюдать','','','research'),
('research.solution.compare_costs','ru','Сравнить net-результат вариантов после подтверждённых издержек','Сравнить net','Сравнить','','','research'),
('research.solution.connect_quotes','ru','Подключить bid/ask, сделки и стакан; затем повторить оценку','Подключить котировки','Котировки','','','research'),
('column.trials','ru','Испытания','Исп.','Исп.','','','column'),
('column.passed','ru','PASS','PASS','PASS','','','column'),
('column.strategy','ru','Стратегия','Стратегия','Стратегия','','','column'),
('column.risk_score','ru','Риск','Риск','Риск','','','column'),
('column.position_risk','ru','Риск позиции','Позиция','Позиция','','','column'),
('column.exposure_risk','ru','Экспозиция','Экспоз.','Экспоз.','','','column'),
('column.decision','ru','Решение policy','Решение','Решение','','','column'),
('column.paper_allowed','ru','Paper разрешён','Paper','Paper','','','column'),
('column.parameters','ru','Параметры','Параметры','Парам.','','','column'),
('column.folds','ru','Фолды','Фолды','Фолды','','','column'),
('column.solution','ru','Вариант решения','Решение','Решение','','','column'),
('column.mode','ru','Режим','Режим','Режим','','','column'),
('column.fills','ru','Исполнения','Исполн.','Исп.','','','column'),
('column.linked_fills','ru','Связаны с сигналом','Связаны','Связь','','','column'),
('column.commission','ru','Комиссия','Комиссия','Комис.','','','column'),
('column.quotes_quality','ru','Bid/ask и стакан','Котировки','Котир.','','','column'),
('status.allowed','ru','Разрешено','Да','Да','','','status'),
('status.not_verified','ru','Не подтверждено','Нет данных','Нет','','','status')
ON CONFLICT (resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

UPDATE presentation.control_center_recommendation_route_v1
SET action_target = CASE reason_group
    WHEN 'VOLATILITY' THEN '/workspace-v2/control-center/edge-oos#volatility-analysis'
    WHEN 'RISK' THEN '/workspace-v2/control-center/edge-oos#risk-analysis'
    WHEN 'SETUP' THEN '/workspace-v2/control-center/edge-oos#entry-analysis'
    WHEN 'EXECUTION' THEN '/workspace-v2/control-center/edge-oos#execution-quality'
    ELSE action_target END,
    source_version='CONTROL_CENTER_ACTION_ANALYSIS_V1', updated_at=now()
WHERE reason_group IN ('VOLATILITY','RISK','SETUP','EXECUTION');
