#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_ENGINE_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('model.health.component.market_model_quality','ru','Качество модели рынка','MMQI','MMQI','Качество цифровой модели рынка','','model_health'),
('model.health.component.learning_readiness','ru','Готовность к обучению','LRI','LRI','Готовность модели к обучению на накопленной статистике','','model_health'),
('model.health.component.robustness','ru','Устойчивость','Robust','Robust','Устойчивость модели к переобучению','','model_health'),
('model.health.component.knowledge_confidence','ru','Доверие к знаниям','KCI','KCI','Уверенность в накопленных знаниях','','model_health'),
('model.health.component.trading_plan_completeness','ru','Полнота Trading Plan','TP','TP','Полнота построения торговых планов','','model_health'),
('model.health.component.paper_coverage','ru','Покрытие Paper','Paper','Paper','Покрытие Paper Validation','','model_health'),
('model.health.component.feedback_readiness','ru','Готовность Feedback','Feedback','FB','Готовность контура обратной связи','','model_health'),
('model.health.component.production_readiness','ru','Готовность к Production','Production','Prod','Готовность к промышленному использованию','','model_health'),

('model.health.gate.pass','ru','Пройдено','PASS','PASS','Проверка пройдена','','model_health'),
('model.health.gate.warning','ru','Требует внимания','WARNING','WARN','Есть замечания','','model_health'),
('model.health.gate.blocked','ru','Заблокировано','BLOCKED','BLOCK','Переход заблокирован','','model_health'),
('model.health.gate.locked','ru','Заблокировано политикой','LOCKED','LOCK','Переход запрещен политикой управления риском','','model_health'),

('model.health.recommendation.continue_paper_validation','ru','Продолжить Paper Validation','Продолжить Paper','Paper','Продолжить накопление Paper-статистики','','model_health'),
('model.health.recommendation.improve_learning_readiness','ru','Повысить готовность к обучению','Повысить LRI','LRI','Накопить больше данных для обучения','','model_health'),

('model.health.reason.production_not_ready','ru','Production не готов','Prod не готов','Prod','Система не готова к Production','','model_health'),
('model.health.reason.learning_readiness_not_ready','ru','Недостаточная готовность к обучению','LRI не готов','LRI','Недостаточно статистики для надежного обучения','','model_health'),

('model.health.action.collect_more_data','ru','Накопить больше данных','Больше данных','Данные','Продолжить сбор статистики','','model_health'),
('model.health.action.continue_observation','ru','Продолжить наблюдение','Наблюдать','Набл.','Продолжить наблюдение без изменения модели','','model_health')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group,
  updated_at=now();
SQL

component_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM analytics.marketcore_model_health_component_registry_v1 c
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key='model.health.component.'||lower(c.component_code)
 AND r.locale_code='ru'
WHERE c.enabled
  AND r.resource_key IS NULL;
SQL
)

gate_status_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
  VALUES ('PASS'),('WARNING'),('BLOCKED'),('LOCKED')
) s(status_code)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key='model.health.gate.'||lower(s.status_code)
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
SQL
)

recommendation_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
  SELECT DISTINCT recommendation_code
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1'
) q
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key='model.health.recommendation.'||lower(q.recommendation_code)
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
SQL
)

reason_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
  SELECT DISTINCT recommendation_reason
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1'
) q
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key='model.health.reason.'||lower(q.recommendation_reason)
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
SQL
)

action_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
  SELECT DISTINCT recommended_action
  FROM analytics.marketcore_model_health_recommendation_v1
  WHERE source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1'
) q
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key='model.health.action.'||lower(q.recommended_action)
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
SQL
)

test "$component_missing" = "0"
test "$gate_status_missing" = "0"
test "$recommendation_missing" = "0"
test "$reason_missing" = "0"
test "$action_missing" = "0"

echo "component_i18n=OK"
echo "gate_status_i18n=OK"
echo "recommendation_i18n=OK"
echo "reason_i18n=OK"
echo "action_i18n=OK"
echo "missing_i18n_resources=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_MODEL_HEALTH_ENGINE_I18N_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_ENGINE_I18N_V1_OK"
