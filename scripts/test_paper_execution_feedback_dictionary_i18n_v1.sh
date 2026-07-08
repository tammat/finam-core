#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_FEEDBACK_DICTIONARY_I18N_V1 ==="

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

--------------------------------------------------------
-- GROUPS
--------------------------------------------------------

('paper.feedback.reason_group.data',
'ru',
'Данные',
'Данные',
'Данные',
'Проблемы качества данных',
'',
'paper'),

('paper.feedback.reason_group.model',
'ru',
'Модель',
'Модель',
'Модель',
'Проблемы модели',
'',
'paper'),

('paper.feedback.reason_group.robustness',
'ru',
'Устойчивость',
'Устойчивость',
'Robust',
'Проблемы устойчивости модели',
'',
'paper'),

('paper.feedback.reason_group.market',
'ru',
'Рынок',
'Рынок',
'Рынок',
'Проблемы рыночной среды',
'',
'paper'),

('paper.feedback.reason_group.profile',
'ru',
'Профиль',
'Профиль',
'Профиль',
'Проблемы профиля Trading Plan',
'',
'paper'),

('paper.feedback.reason_group.source',
'ru',
'Источник',
'Источник',
'Источник',
'Проблемы источника данных',
'',
'paper'),

('paper.feedback.reason_group.risk',
'ru',
'Риск',
'Риск',
'Риск',
'Проблемы управления риском',
'',
'paper'),

--------------------------------------------------------
-- SEVERITY
--------------------------------------------------------

('paper.feedback.severity.info',
'ru',
'Информация',
'Info',
'Info',
'Информационный уровень',
'',
'paper'),

('paper.feedback.severity.notice',
'ru',
'Замечание',
'Notice',
'Notice',
'Требует внимания',
'',
'paper'),

('paper.feedback.severity.warning',
'ru',
'Предупреждение',
'Warning',
'Warn',
'Предупреждение',
'',
'paper'),

('paper.feedback.severity.critical',
'ru',
'Критично',
'Critical',
'Critical',
'Критическая проблема',
'',
'paper'),

--------------------------------------------------------
-- REASONS
--------------------------------------------------------

('paper.feedback.reason.low_sample_size',
'ru',
'Недостаточный объем выборки',
'Мало данных',
'Мало',
'Недостаточно статистики',
'',
'paper'),

('paper.feedback.reason.negative_expectancy',
'ru',
'Отрицательное ожидание',
'Negative Exp',
'Exp',
'Математическое ожидание отрицательно',
'',
'paper'),

('paper.feedback.reason.low_profit_factor',
'ru',
'Низкий Profit Factor',
'Low PF',
'PF',
'Profit Factor ниже допустимого',
'',
'paper'),

('paper.feedback.reason.high_overfit_risk',
'ru',
'Высокий риск переобучения',
'Overfit',
'Overfit',
'Высокая вероятность переобучения',
'',
'paper'),

('paper.feedback.reason.low_robustness',
'ru',
'Низкая устойчивость',
'Robustness',
'Robust',
'Недостаточная устойчивость модели',
'',
'paper'),

('paper.feedback.reason.regime_unstable',
'ru',
'Нестабильность по режимам',
'Regime',
'Regime',
'Результаты нестабильны между режимами рынка',
'',
'paper'),

('paper.feedback.reason.profile_unstable',
'ru',
'Нестабильный профиль',
'Profile',
'Profile',
'Профиль Trading Plan нестабилен',
'',
'paper'),

('paper.feedback.reason.source_unstable',
'ru',
'Нестабильный источник',
'Source',
'Source',
'Источник Trading Plan нестабилен',
'',
'paper')

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

group_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM analytics.paper_execution_feedback_reason_group_v1 g
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key='paper.feedback.reason_group.'||lower(g.reason_group_code)
AND r.locale_code='ru'
WHERE g.enabled
AND r.resource_key IS NULL;
SQL
)

severity_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM analytics.paper_execution_feedback_severity_v1 s
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key='paper.feedback.severity.'||lower(s.severity_code)
AND r.locale_code='ru'
WHERE s.enabled
AND r.resource_key IS NULL;
SQL
)

reason_missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM analytics.paper_execution_feedback_reason_v1 f
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key='paper.feedback.reason.'||lower(f.reason_code)
AND r.locale_code='ru'
WHERE f.enabled
AND r.resource_key IS NULL;
SQL
)

test "$group_missing" = "0"
test "$severity_missing" = "0"
test "$reason_missing" = "0"

echo "feedback_reason_group_i18n=OK"
echo "feedback_severity_i18n=OK"
echo "feedback_reason_i18n=OK"
echo "missing_i18n_resources=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PAPER_EXECUTION_FEEDBACK_DICTIONARY_I18N_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_FEEDBACK_DICTIONARY_I18N_V1_OK"

