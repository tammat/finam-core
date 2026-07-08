#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_FEEDBACK_ENGINE_I18N_V1 ==="

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

('widget.paper_feedback_engine.title',
'ru',
'Рекомендации модели',
'Feedback',
'Feedback',
'Рекомендации по улучшению модели',
'💡',
'paper'),

----------------------------------------------------------
-- Engine fields
----------------------------------------------------------

('paper.feedback.rule',
'ru',
'Правило',
'Правило',
'Rule',
'Правило формирования рекомендации',
'',
'paper'),

('paper.feedback.rule_code',
'ru',
'Код правила',
'Код',
'Rule',
'Код правила',
'',
'paper'),

('paper.feedback.reason_code',
'ru',
'Код причины',
'Причина',
'Reason',
'Код причины рекомендации',
'',
'paper'),

('paper.feedback.severity_code',
'ru',
'Критичность',
'Severity',
'Severity',
'Уровень критичности',
'',
'paper'),

('paper.feedback.action_code',
'ru',
'Рекомендуемое действие',
'Action',
'Action',
'Код рекомендуемого действия',
'',
'paper'),

('paper.feedback.scope_code',
'ru',
'Область',
'Scope',
'Scope',
'Область применения рекомендации',
'',
'paper'),

('paper.feedback.feedback_target',
'ru',
'Объект',
'Target',
'Target',
'Объект рекомендации',
'',
'paper'),

----------------------------------------------------------
-- Sample status
----------------------------------------------------------

('paper.feedback.sample_status.research',
'ru',
'Исследование',
'Research',
'Research',
'Недостаточно статистики',
'',
'paper'),

('paper.feedback.sample_status.validated',
'ru',
'Подтверждено',
'Validated',
'Validated',
'Статистически подтверждено',
'',
'paper'),

('paper.feedback.sample_status.production',
'ru',
'Production',
'Production',
'Production',
'Допущено к использованию',
'',
'paper'),

----------------------------------------------------------
-- Overfit
----------------------------------------------------------

('paper.feedback.overfit.low',
'ru',
'Низкий',
'Low',
'Low',
'Низкий риск переобучения',
'',
'paper'),

('paper.feedback.overfit.medium',
'ru',
'Средний',
'Medium',
'Medium',
'Средний риск переобучения',
'',
'paper'),

('paper.feedback.overfit.high',
'ru',
'Высокий',
'High',
'High',
'Высокий риск переобучения',
'',
'paper')

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
('widget.paper_feedback_engine.title'),
('paper.feedback.rule'),
('paper.feedback.rule_code'),
('paper.feedback.reason_code'),
('paper.feedback.severity_code'),
('paper.feedback.action_code'),
('paper.feedback.scope_code'),
('paper.feedback.feedback_target'),
('paper.feedback.sample_status.research'),
('paper.feedback.sample_status.validated'),
('paper.feedback.sample_status.production'),
('paper.feedback.overfit.low'),
('paper.feedback.overfit.medium'),
('paper.feedback.overfit.high')
) t(resource_key)

LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key=t.resource_key
AND r.locale_code='ru'

WHERE r.resource_key IS NULL;
SQL
)

test "$missing" = "0"

echo "feedback_engine_i18n=OK"
echo "missing_i18n_resources=0"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PAPER_EXECUTION_FEEDBACK_ENGINE_I18N_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_FEEDBACK_ENGINE_I18N_V1_OK"

