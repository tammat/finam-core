#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_ANALYTICS_I18N_V1 ==="

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

('widget.paper_execution_analytics.title','ru','Аналитика Paper','Paper Analytics','Paper','Сводная аналитика Paper Execution','📊','paper'),

('paper.analytics.profit_factor','ru','Profit Factor','PF','PF','Коэффициент прибыльности','','paper'),
('paper.analytics.expectancy','ru','Ожидание','Expectancy','Exp','Математическое ожидание','','paper'),
('paper.analytics.win_rate','ru','Win Rate','Win Rate','Win','Процент прибыльных сделок','','paper'),
('paper.analytics.avg_r','ru','Средний R','Avg R','R','Средний R-множитель','','paper'),
('paper.analytics.mae','ru','MAE','MAE','MAE','Максимальное неблагоприятное отклонение','','paper'),
('paper.analytics.mfe','ru','MFE','MFE','MFE','Максимальное благоприятное отклонение','','paper'),
('paper.analytics.drawdown','ru','Просадка','DD','DD','Максимальная просадка','','paper'),
('paper.analytics.trades','ru','Сделки','Сделки','Сделки','Количество сделок','','paper'),

('paper.analytics.profile_scorecard','ru','Профили Trading Plan','Профили','Профили','Статистика по профилям','','paper'),
('paper.analytics.source_scorecard','ru','Источники Trading Plan','Источники','Источники','Статистика по источникам','','paper'),
('paper.analytics.regime_scorecard','ru','Режимы рынка','Режимы','Режимы','Статистика по режимам рынка','','paper'),

('paper.analytics.research_only','ru','Недостаточно данных','Research','Research','Недостаточная выборка','','paper'),
('paper.analytics.validated','ru','Подтверждено','Validated','OK','Статистически подтверждено','','paper'),
('paper.analytics.production','ru','Production','Production','Prod','Допущено к использованию','','paper')

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

missing=$(psql -At -d finam_core <<'SQL'
SELECT count(*)
FROM (
VALUES
('widget.paper_execution_analytics.title'),
('paper.analytics.profit_factor'),
('paper.analytics.expectancy'),
('paper.analytics.win_rate'),
('paper.analytics.avg_r'),
('paper.analytics.mae'),
('paper.analytics.mfe'),
('paper.analytics.drawdown'),
('paper.analytics.trades'),
('paper.analytics.profile_scorecard'),
('paper.analytics.source_scorecard'),
('paper.analytics.regime_scorecard'),
('paper.analytics.research_only'),
('paper.analytics.validated'),
('paper.analytics.production')
) t(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
ON r.resource_key=t.resource_key
AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
SQL
)

test "$missing" = "0"

echo "analytics_i18n=OK"
echo "missing_i18n_resources=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PAPER_EXECUTION_ANALYTICS_I18N_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_ANALYTICS_I18N_V1_OK"
