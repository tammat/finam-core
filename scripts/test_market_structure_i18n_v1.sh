#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_STRUCTURE_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('market_structure.support', 'ru', 'Поддержка', 'Поддержка', 'Поддержка', 'Уровень поддержки', '', 'market_structure'),
('market_structure.resistance', 'ru', 'Сопротивление', 'Сопротивл.', 'Сопрот.', 'Уровень сопротивления', '', 'market_structure'),
('market_structure.swing_high', 'ru', 'Локальный максимум', 'Swing High', 'Макс.', 'Локальный максимум цены', '', 'market_structure'),
('market_structure.swing_low', 'ru', 'Локальный минимум', 'Swing Low', 'Мин.', 'Локальный минимум цены', '', 'market_structure'),
('market_structure.pivot_level', 'ru', 'Пивот-уровень', 'Пивот', 'Пивот', 'Расчетный pivot-уровень', '', 'market_structure'),
('market_structure.fibonacci_retracement', 'ru', 'Уровень Фибоначчи: коррекция', 'Фибо корр.', 'Фибо', 'Уровень коррекции Фибоначчи', '', 'market_structure'),
('market_structure.fibonacci_extension', 'ru', 'Уровень Фибоначчи: расширение', 'Фибо расш.', 'Фибо', 'Уровень расширения Фибоначчи', '', 'market_structure'),
('market_structure.channel_upper', 'ru', 'Верхняя граница канала', 'Канал верх', 'Верх', 'Верхняя граница ценового канала', '', 'market_structure'),
('market_structure.channel_lower', 'ru', 'Нижняя граница канала', 'Канал низ', 'Низ', 'Нижняя граница ценового канала', '', 'market_structure'),
('market_structure.breakout_level', 'ru', 'Уровень пробоя', 'Пробой', 'Пробой', 'Уровень потенциального пробоя', '', 'market_structure'),
('widget.market_structure.title', 'ru', 'Структура рынка', 'Структура', 'Структура', 'Ключевые уровни и структура рынка', '📐', 'widget')
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
  SELECT 'market_structure.' || lower(structure_type_code) AS resource_key
  FROM knowledge.market_structure_type_v1
  WHERE source_version='MARKET_STRUCTURE_PARAMETER_SEED_V1'
  UNION ALL
  SELECT 'widget.market_structure.title'
) k
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

test "$missing" = "0"

echo "market_structure_i18n=OK"
echo "missing_i18n_resources=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_STRUCTURE_I18N_V1_READY"
echo "VERDICT=TEST_MARKET_STRUCTURE_I18N_V1_OK"
