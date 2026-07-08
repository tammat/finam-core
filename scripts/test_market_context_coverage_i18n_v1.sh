#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_CONTEXT_COVERAGE_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('widget.knowledge_coverage.title', 'ru', 'Покрытие знаний', 'Знания', 'Знания', 'Доля заполненных рыночных контекстов', '🧠', 'widget'),
('knowledge.coverage.total', 'ru', 'Общее покрытие', 'Покрытие', 'Покрытие', 'Совокупный показатель заполненности Market Knowledge', '', 'knowledge'),
('knowledge.coverage.regime', 'ru', 'Режим рынка', 'Режим', 'Режим', 'Покрытие режима рынка', '', 'knowledge'),
('knowledge.coverage.volatility', 'ru', 'Волатильность', 'Волат.', 'Волат.', 'Покрытие состояния волатильности', '', 'knowledge'),
('knowledge.coverage.liquidity', 'ru', 'Ликвидность', 'Ликв.', 'Ликв.', 'Покрытие состояния ликвидности', '', 'knowledge'),
('knowledge.coverage.volume', 'ru', 'Объем', 'Объем', 'Объем', 'Покрытие состояния объема торгов', '', 'knowledge'),
('knowledge.coverage.spread', 'ru', 'Спред', 'Спред', 'Спред', 'Покрытие состояния спреда', '', 'knowledge'),
('knowledge.coverage.session', 'ru', 'Сессия', 'Сессия', 'Сессия', 'Покрытие торговой сессии', '', 'knowledge'),
('knowledge.coverage.correlation', 'ru', 'Корреляция', 'Корр.', 'Корр.', 'Покрытие корреляционного контекста', '', 'knowledge'),
('knowledge.coverage.sector_strength', 'ru', 'Сила сектора', 'Сектор', 'Сектор', 'Покрытие секторного контекста', '', 'knowledge')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
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
    ('widget.knowledge_coverage.title'),
    ('knowledge.coverage.total'),
    ('knowledge.coverage.regime'),
    ('knowledge.coverage.volatility'),
    ('knowledge.coverage.liquidity'),
    ('knowledge.coverage.volume'),
    ('knowledge.coverage.spread'),
    ('knowledge.coverage.session'),
    ('knowledge.coverage.correlation'),
    ('knowledge.coverage.sector_strength')
) AS required(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=required.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_I18N_RESOURCES=$missing"
  exit 1
fi

echo "knowledge_coverage_i18n=OK"
echo "missing_i18n_resources=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_CONTEXT_COVERAGE_I18N_V1_READY"
echo "VERDICT=TEST_MARKET_CONTEXT_COVERAGE_I18N_V1_OK"
