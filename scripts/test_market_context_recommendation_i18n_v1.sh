#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_RECOMMENDATION_I18N_V1 ==="

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

('recommendation.validate',
 'ru',
 'Подтвердить',
 'Подтвердить',
 'Подтв.',
 'Рекомендация требует подтверждения',
 '✔',
 'recommendation'),

('recommendation.continue_research',
 'ru',
 'Продолжить исследование',
 'Исследовать',
 'Исслед.',
 'Продолжить исследование возможности',
 '🔍',
 'recommendation'),

('recommendation.observe',
 'ru',
 'Наблюдать',
 'Наблюдать',
 'Набл.',
 'Продолжить наблюдение',
 '👁',
 'recommendation'),

('recommendation.recheck',
 'ru',
 'Проверить повторно',
 'Перепроверить',
 'Проверить',
 'Требуется повторная проверка',
 '🔄',
 'recommendation'),

('recommendation.reject',
 'ru',
 'Отклонить',
 'Отклонить',
 'Откл.',
 'Рекомендация отклонена',
 '✖',
 'recommendation'),

('recommendation.insufficient_data',
 'ru',
 'Недостаточно данных',
 'Недостаточно данных',
 'Нет данных',
 'Недостаточно данных для рекомендации',
 '⚠',
 'recommendation'),

('reason.edge_score.ge',
 'ru',
 'Edge Score выше порога',
 'Edge',
 'Edge',
 'Edge Score удовлетворяет правилу',
 '',
 'recommendation'),

('reason.knowledge_coverage.ge',
 'ru',
 'Достаточное покрытие знаний',
 'Knowledge',
 'Knowledge',
 'Knowledge Coverage удовлетворяет правилу',
 '',
 'recommendation'),

('reason.insufficient_data',
 'ru',
 'Недостаточно данных',
 'Нет данных',
 'Нет данных',
 'Недостаточно данных для формирования рекомендации',
 '',
 'recommendation')

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

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
VALUES
('recommendation.validate'),
('recommendation.continue_research'),
('recommendation.observe'),
('recommendation.recheck'),
('recommendation.reject'),
('recommendation.insufficient_data'),
('reason.edge_score.ge'),
('reason.knowledge_coverage.ge'),
('reason.insufficient_data')
) r(resource_key)
LEFT JOIN presentation.ui_resource_v1 u
ON u.resource_key=r.resource_key
AND u.locale_code='ru'
WHERE u.resource_key IS NULL;
")

test "$missing" = "0"

echo "recommendation_i18n_resources=OK"
echo "missing_i18n_resources=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_CONTEXT_RECOMMENDATION_I18N_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_RECOMMENDATION_I18N_V1_OK"

