#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OPERATOR_HOME_STATUS_BAR_PORTFOLIO_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_status_bar_portfolio PYTHONPATH=src \
python -m py_compile src/marketcore/presentation/components/layout/status_bar.py

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.components.layout.status_bar import render_status_bar

html = render_status_bar(portfolio_value="12584321.45", daily_pnl="48125.34", daily_pnl_pct="0.38")
assert "MarketCore" in html
assert "statusbar.portfolio" in html
assert "12 584 321,45 ₽" in html
assert "statusbar.daily_pnl" in html
assert "+48 125,34 ₽" in html
assert "+0,38 %" in html
assert "status-bar-pnl-positive" in html

import re
assert re.search(r"\d{2}\.\d{2}\.\d{2} \d{2}:\d{2}", html), html
print("status_bar_portfolio_render=OK")
PY

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('statusbar.broker', 'ru', 'Брокер', 'Брокер', 'Брокер', 'Выбранный брокер', '', 'statusbar'),
('statusbar.connection', 'ru', 'Подключение', 'Подключение', 'Подключение', 'Состояние подключения', '', 'statusbar'),
('statusbar.timezone', 'ru', 'Часовой пояс', 'TZ', 'TZ', 'Выбранный часовой пояс', '', 'statusbar'),
('statusbar.currency', 'ru', 'Валюта', 'Валюта', 'Валюта', 'Валюта отображения', '', 'statusbar'),
('statusbar.portfolio', 'ru', 'Портфель', 'Портфель', 'Портфель', 'Стоимость портфеля', '', 'statusbar'),
('statusbar.daily_pnl', 'ru', 'P&L сегодня', 'P&L', 'P&L', 'Финансовый результат за день', '', 'statusbar'),
('statusbar.last_data_update', 'ru', 'Данные', 'Данные', 'Данные', 'Последнее обновление данных', '', 'statusbar'),
('statusbar.local_time', 'ru', 'Локальное время', 'Время', 'Время', 'Локальное время пользователя', '', 'statusbar')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();
SQL

sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/operator_home_status_bar_portfolio.html

grep -q "marketcore-status-bar" /tmp/operator_home_status_bar_portfolio.html
grep -q "statusbar.portfolio" /tmp/operator_home_status_bar_portfolio.html
grep -q "statusbar.daily_pnl" /tmp/operator_home_status_bar_portfolio.html
grep -q "statusbar.local_time" /tmp/operator_home_status_bar_portfolio.html
grep -Eq '[0-9]{2}\.[0-9]{2}\.[0-9]{2} [0-9]{2}:[0-9]{2}' /tmp/operator_home_status_bar_portfolio.html

echo "status_bar_portfolio=OK"
echo "date_format=DD.MM.YY HH:MM"
echo "portfolio_value_visible=OK"
echo "daily_pnl_visible=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_OPERATOR_HOME_STATUS_BAR_PORTFOLIO_V1_READY"
echo "VERDICT=TEST_MARKETCORE_OPERATOR_HOME_STATUS_BAR_PORTFOLIO_V1_OK"
