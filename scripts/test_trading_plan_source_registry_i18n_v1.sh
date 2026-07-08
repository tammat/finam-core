#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_SOURCE_REGISTRY_I18N_V1 ==="

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

SELECT

'trading_plan.source.'||lower(source_code),

'ru',

source_name,

source_name,

source_name,

source_name,

'',

'trading_plan'

FROM knowledge.trading_plan_source_v1

ON CONFLICT(resource_key,locale_code)

DO UPDATE SET

caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,
updated_at=now();

SQL

echo "VERDICT=TRADING_PLAN_SOURCE_REGISTRY_I18N_V1_READY"
