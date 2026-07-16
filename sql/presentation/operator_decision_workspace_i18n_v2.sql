INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('home.operator.actions.section.title','ru','Действия оператора','Действия','Действ.','Ранжированные решения на основе подтверждённых источников','', 'operator_decision_v2'),
('home.operator.actions.section.subtitle','ru','Непроверенные данные не разрешают автоматическое продвижение','Требуется проверка','Проверка','Каждое действие содержит срок, режим автономности и план отката','', 'operator_decision_v2'),
('home.operator.action.title','ru','Рекомендуемое действие','Действие','Действ.','Действие из управляемой политики','', 'operator_decision_v2'),
('home.operator.action.subtitle','ru','Требуется решение оператора','Решение оператора','Решение','Автоматическое исполнение отключено','', 'operator_decision_v2'),
('home.operator.field.loss_source','ru','Источник потерь','Источник','Источник','Причина узкого места','', 'operator_decision_v2'),
('home.operator.field.expected_profit_impact','ru','Ожидаемый эффект на прибыль','Эффект','Эффект','Оценка эффекта в рублях','', 'operator_decision_v2'),
('home.operator.field.risk_impact','ru','Влияние на риск','Риск','Риск','Ожидаемое изменение риска','', 'operator_decision_v2'),
('home.operator.field.confidence','ru','Уверенность','Уверенность','Увер.','Уверенность с учётом качества источника','', 'operator_decision_v2'),
('home.operator.field.sample_size','ru','Размер выборки','Выборка','Выб.','Количество наблюдений','', 'operator_decision_v2'),
('home.operator.field.sample_sufficiency','ru','Достаточность выборки','Достаточность','Достат.','Оценка достаточности наблюдений','', 'operator_decision_v2'),
('home.operator.field.policy_verdict','ru','Вердикт политики','Вердикт','Вердикт','Решение Policy Engine','', 'operator_decision_v2'),
('home.operator.field.autonomy_mode','ru','Режим автономности','Автономность','Автон.','Разрешённый уровень автономности','', 'operator_decision_v2'),
('home.operator.field.expires_at','ru','Действительно до','Срок','Срок','Время окончания действия решения','', 'operator_decision_v2'),
('home.operator.field.rollback','ru','План отката','Откат','Откат','Действие при отмене решения','', 'operator_decision_v2'),
('home.operator.field.feedback','ru','Обратная связь','Результат','Результ.','Состояние измерения фактического результата','', 'operator_decision_v2'),
('home.operator.field.selection','ru','Выбор оператора','Выбор','Выбор','Состояние рассмотрения решения оператором','', 'operator_decision_v2'),
('home.operator.field.baseline','ru','Исходное значение','Исходное','Исх.','Значение показателя в момент выбора','', 'operator_decision_v2'),
('home.operator.field.measurement_due','ru','Измерить после','Измерение','Измер.','Минимальное время наблюдения результата','', 'operator_decision_v2'),
('home.operator.field.actual_result','ru','Фактический результат','Результат','Результ.','Изменение показателя относительно исходного значения','', 'operator_decision_v2')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
