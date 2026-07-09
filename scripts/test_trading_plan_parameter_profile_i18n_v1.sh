#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_PARAMETER_PROFILE_I18N_V1 ==="

psql -d finam_core <<'SQL'

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

('trading_plan.profile.default',
'ru',
'Профиль по умолчанию',
'По умолчанию',
'Стандарт',
'Стандартный профиль построения Trading Plan',
'',
'trading_plan'),

('trading_plan.profile.conservative',
'ru',
'Консервативный профиль',
'Консервативный',
'Консерват.',
'Консервативный профиль',
'',
'trading_plan'),

('trading_plan.profile.momentum',
'ru',
'Профиль импульса',
'Импульс',
'Импульс',
'Профиль для импульсных стратегий',
'',
'trading_plan')

ON CONFLICT(resource_key,locale_code)
DO UPDATE SET

caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
updated_at=now();

SQL

echo "VERDICT=TRADING_PLAN_PARAMETER_PROFILE_I18N_V1_READY"
