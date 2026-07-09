#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_MODEL_HEALTH_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'

INSERT INTO presentation.ui_resource_v1
(
    resource_key,
    locale_code,
    caption,
    caption_short,
    caption_mobile,
    tooltip,
    icon,
    resource_group
)
VALUES

----------------------------------------------------------
-- Widget
----------------------------------------------------------

('widget.model_health.title',
'ru',
'Здоровье модели',
'Model Health',
'Health',
'Сводная оценка зрелости модели',
'🩺',
'model_health'),

----------------------------------------------------------
-- Components
----------------------------------------------------------

('model.health.market_model_quality',
'ru',
'Качество модели рынка',
'MMQI',
'MMQI',
'Market Model Quality Index',
'',
'model_health'),

('model.health.learning_readiness',
'ru',
'Готовность к обучению',
'LRI',
'LRI',
'Learning Readiness Index',
'',
'model_health'),

('model.health.robustness',
'ru',
'Устойчивость модели',
'Robustness',
'Robust',
'Robustness Score',
'',
'model_health'),

('model.health.knowledge_confidence',
'ru',
'Доверие к знаниям',
'Knowledge',
'KCI',
'Knowledge Confidence Index',
'',
'model_health'),

('model.health.trading_plan_completeness',
'ru',
'Полнота Trading Plan',
'Trading Plan',
'TP',
'Полнота торгового плана',
'',
'model_health'),

('model.health.paper_coverage',
'ru',
'Покрытие Paper',
'Paper',
'Paper',
'Покрытие Paper Validation',
'',
'model_health'),

('model.health.feedback_readiness',
'ru',
'Готовность Feedback',
'Feedback',
'FB',
'Готовность обратной связи',
'',
'model_health'),

('model.health.production_readiness',
'ru',
'Готовность к Production',
'Production',
'Prod',
'Production Readiness',
'',
'model_health'),

----------------------------------------------------------
-- Gates
----------------------------------------------------------

('model.health.gate.paper',
'ru',
'Paper Validation',
'Paper',
'Paper',
'Проверка Paper Validation',
'',
'model_health'),

('model.health.gate.analytics',
'ru',
'Аналитика',
'Analytics',
'Analytics',
'Проверка аналитики',
'',
'model_health'),

('model.health.gate.robustness',
'ru',
'Устойчивость',
'Robustness',
'Robust',
'Проверка устойчивости модели',
'',
'model_health'),

('model.health.gate.feedback',
'ru',
'Feedback',
'Feedback',
'Feedback',
'Проверка обратной связи',
'',
'model_health'),

('model.health.gate.production',
'ru',
'Production',
'Production',
'Prod',
'Готовность к Production',
'',
'model_health'),

----------------------------------------------------------
-- Gate status
----------------------------------------------------------

('model.health.status.pass',
'ru',
'Пройдено',
'PASS',
'PASS',
'Проверка успешно пройдена',
'',
'model_health'),

('model.health.status.warning',
'ru',
'Требует внимания',
'WARNING',
'WARN',
'Есть замечания',
'',
'model_health'),

('model.health.status.blocked',
'ru',
'Заблокировано',
'BLOCKED',
'BLOCK',
'Переход запрещен',
'',
'model_health'),

('model.health.status.locked',
'ru',
'Заблокировано политикой',
'LOCKED',
'LOCK',
'Следующий этап недоступен',
'',
'model_health')

ON CONFLICT(resource_key,locale_code)
DO UPDATE SET

caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,
resource_group=EXCLUDED.resource_group,
updated_at=now();

SQL

missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
VALUES
('widget.model_health.title'),
('model.health.market_model_quality'),
('model.health.learning_readiness'),
('model.health.robustness'),
('model.health.knowledge_confidence'),
('model.health.trading_plan_completeness'),
('model.health.paper_coverage'),
('model.health.feedback_readiness'),
('model.health.production_readiness'),
('model.health.gate.paper'),
('model.health.gate.analytics'),
('model.health.gate.robustness'),
('model.health.gate.feedback'),
('model.health.gate.production'),
('model.health.status.pass'),
('model.health.status.warning'),
('model.health.status.blocked'),
('model.health.status.locked')
) t(resource_key)

LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key=t.resource_key
AND r.locale_code='ru'

WHERE r.resource_key IS NULL;
SQL
)

test "$missing" = "0"

echo "model_health_i18n=OK"
echo "missing_i18n_resources=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_MODEL_HEALTH_I18N_V1_READY"
echo "VERDICT=TEST_MARKETCORE_MODEL_HEALTH_I18N_V1_OK"

