BEGIN;
INSERT INTO presentation.ui_resource_v1
 (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
 ('home.operator.edge_search.summary','ru','{status} · {stage} · {progress}% · проверено {variants} · PASS {passes}','{stage} · {progress}% · PASS {passes}','{progress}% · PASS {passes}','Текущая стадия автономного поиска, фактический прогресс и число подтверждений.','','workspace_v2_home_operator'),
 ('home.operator.model_health.summary','ru','Проверок {checks} · замечаний {recommendations}','Проверок {checks} · замечаний {recommendations}','Проверок {checks}','Число сохранённых проверок здоровья моделей и активных рекомендаций.','','workspace_v2_home_operator'),
 ('home.operator.signal_funnel.summary','ru','Сигналы {signals} → заявки {orders} → сделки {trades} · допуск {conversion}%','{signals} → {orders} → {trades} · {conversion}%','{signals} → {trades}','Последняя сопоставимая когорта: сигналы, допущенные заявки и зарегистрированные сделки.','','workspace_v2_home_operator'),
 ('column.operator.next','ru','Далее','Далее','Далее','Что оператор может сделать сейчас.','','column'),
 ('home.operator.next.open','ru','Выбрать действие','Выбрать','Открыть','Двойной клик открывает рекомендуемые действия.','','operator_decision_v2'),
 ('home.operator.next.wait','ru','Ждать подтверждения','Ожидать','Ждать','Действие пока недоступно: требуется подтверждённый источник или допуск.','','operator_decision_v2'),
 ('home.operator.next.refresh','ru','Обновить решение','Обновить','Обновить','Срок решения истёк; система должна сформировать актуальную рекомендацию.','','operator_decision_v2')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
 caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
 resource_group=EXCLUDED.resource_group;
COMMIT;
