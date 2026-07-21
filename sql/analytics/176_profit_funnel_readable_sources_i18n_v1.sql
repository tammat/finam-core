BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('funnel.source.analytics.edge_discovery_run_v1.latest_done','ru','Завершённые исследования','Исследования','Исслед.','Последний завершённый системный цикл поиска','','funnel'),
('funnel.source.analytics.edge_candidate_v1','ru','Кандидаты edge','Кандидаты','Кандид.','Кандидаты, созданные исследовательским циклом','','funnel'),
('funnel.source.analytics.profit_funnel_validated_edge_v2','ru','Подтверждённое преимущество','Преимущество','Edge','Кандидаты с подтверждённым преимуществом','','funnel'),
('funnel.source.analytics.edge_oos_result_v1','ru','Результаты OOS','OOS','OOS','Результаты независимой вневыборочной проверки','','funnel'),
('funnel.source.analytics.forward_edge_observation_v1','ru','Forward-наблюдение','Forward','Forward','Наблюдения на последующих данных','','funnel'),
('funnel.source.analytics.forward_edge_shadow_trade_v1','ru','Теневые сделки','Shadow','Shadow','Теневые сделки чистой Forward-когорты','','funnel'),
('funnel.source.analytics.paper_runtime_candidate_v1.active_oos_pass','ru','Paper-кандидаты','Paper','Paper','Активные Paper-кандидаты после OOS PASS','','funnel'),
('funnel.source.analytics.profit_funnel_paper_runtime_admission_v2.admitted','ru','Допуск к исполнению','Допуск','Допуск','Аудируемые решения о допуске в Runtime','','funnel'),
('funnel.source.public.orders.exchange_accepted','ru','Биржевые заявки','Биржа','Биржа','Заявки, принятые биржей','','funnel'),
('funnel.source.analytics.profit_factory_profit_fact_v1[data_scope=real]','ru','Подтверждённая прибыль','Прибыль','P&L','Факты реальной реализованной прибыли','','funnel'),
('funnel.conversion.initial_stage','ru','Начало','Начало','Начало','Первая стадия: конверсия не рассчитывается','','funnel'),
('funnel.conversion.candidate_uuid_link_gap','ru','Нет связи','Нет связи','Нет связи','Не подтверждена каноническая связь с кандидатом','','funnel'),
('funnel.conversion.observation_uuid_link_gap','ru','Нет связи','Нет связи','Нет связи','Не подтверждена связь с OOS-наблюдением','','funnel'),
('funnel.conversion.handoff_pending_forward_admission','ru','Ждёт допуска','Ждёт допуска','Допуск','Ожидается допуск к Forward-наблюдению','','funnel'),
('funnel.conversion.canonical_link_not_proven','ru','Нет связи','Нет связи','Нет связи','Каноническая связь между стадиями не подтверждена','','funnel'),
('funnel.conversion.shadow_assessment_gap','ru','Нет Shadow','Нет Shadow','Shadow','Недостаточно подтверждённых Shadow-данных','','funnel'),
('funnel.conversion.runtime_admission_pending','ru','Ждёт допуска','Ждёт допуска','Допуск','Ожидается аудируемое решение о допуске в Runtime','','funnel'),
('funnel.conversion.no_runtime_candidate_admitted','ru','Нет допуска','Нет допуска','Нет допуска','Нет кандидатов, допущенных к исполнению','','funnel'),
('funnel.conversion.no_real_execution','ru','Нет сделок','Нет сделок','Нет сделок','Реальное исполнение отсутствует','','funnel'),
('funnel.conversion.not_calculated','ru','Не рассчитано','Не рассчитано','Нет расчёта','Связь стадий пока не позволяет рассчитать конверсию','','funnel'),
('status.pending','ru','Ожидает','Ожидает','Ожидает','Заявка поставлена в очередь и ещё не взята worker-ом','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=excluded.caption,caption_short=excluded.caption_short,
caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
