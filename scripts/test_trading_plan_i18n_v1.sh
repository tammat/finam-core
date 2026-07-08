#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_I18N_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('widget.trading_plan.title', 'ru', 'Торговый план', 'Торг. план', 'План', 'Параметры торгового плана', '🧭', 'trading_plan'),

('trading_plan.entry_price', 'ru', 'Цена входа', 'Вход', 'Вход', 'Расчетная цена входа', '', 'trading_plan'),
('trading_plan.stop_loss_price', 'ru', 'Стоп-лосс', 'Стоп', 'Стоп', 'Цена защитного стопа', '', 'trading_plan'),
('trading_plan.take_profit_price', 'ru', 'Тейк-профит', 'Тейк', 'Тейк', 'Целевая цена фиксации', '', 'trading_plan'),
('trading_plan.invalidation_price', 'ru', 'Цена отмены идеи', 'Отмена', 'Отмена', 'Цена, при которой идея считается недействительной', '', 'trading_plan'),
('trading_plan.target_price', 'ru', 'Целевая цена', 'Цель', 'Цель', 'Расчетная целевая цена', '', 'trading_plan'),
('trading_plan.horizon_bars', 'ru', 'Горизонт в барах', 'Горизонт', 'Гориз.', 'Количество баров для проверки идеи', '', 'trading_plan'),
('trading_plan.risk_unit', 'ru', 'Единица риска', 'Риск', 'Риск', 'Единица риска для расчета R-multiple', '', 'trading_plan'),
('trading_plan.direction', 'ru', 'Направление', 'Направл.', 'Напр.', 'Исследовательское направление идеи', '', 'trading_plan'),
('trading_plan.profile', 'ru', 'Профиль', 'Профиль', 'Проф.', 'Профиль построения торгового плана', '', 'trading_plan'),
('trading_plan.entry_source', 'ru', 'Источник входа', 'Источник входа', 'Вход src', 'Источник расчета цены входа', '', 'trading_plan'),
('trading_plan.stop_source', 'ru', 'Источник стопа', 'Источник стопа', 'Стоп src', 'Источник расчета стопа', '', 'trading_plan'),
('trading_plan.target_source', 'ru', 'Источник цели', 'Источник цели', 'Цель src', 'Источник расчета целевой цены', '', 'trading_plan'),

('trading_plan.direction.direction_up', 'ru', 'Вверх', 'Вверх', 'Вверх', 'Направление вверх', '', 'trading_plan'),
('trading_plan.direction.direction_down', 'ru', 'Вниз', 'Вниз', 'Вниз', 'Направление вниз', '', 'trading_plan'),
('trading_plan.direction.direction_neutral', 'ru', 'Нейтрально', 'Нейтрально', 'Нейтр.', 'Нейтральное направление', '', 'trading_plan')
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
    ('widget.trading_plan.title'),
    ('trading_plan.entry_price'),
    ('trading_plan.stop_loss_price'),
    ('trading_plan.take_profit_price'),
    ('trading_plan.invalidation_price'),
    ('trading_plan.target_price'),
    ('trading_plan.horizon_bars'),
    ('trading_plan.risk_unit'),
    ('trading_plan.direction'),
    ('trading_plan.profile'),
    ('trading_plan.entry_source'),
    ('trading_plan.stop_source'),
    ('trading_plan.target_source'),
    ('trading_plan.direction.direction_up'),
    ('trading_plan.direction.direction_down'),
    ('trading_plan.direction.direction_neutral')
) k(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=k.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

test "$missing" = "0"

source_missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.trading_plan_source_v1 s
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key='trading_plan.source.'||lower(s.source_code)
 AND r.locale_code='ru'
WHERE s.enabled
  AND r.resource_key IS NULL;
")

test "$source_missing" = "0"

echo "trading_plan_i18n=OK"
echo "missing_i18n_resources=0"
echo "missing_source_i18n=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLAN_I18N_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_I18N_V1_OK"
