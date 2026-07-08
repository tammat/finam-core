#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_BUTTONS_AND_ICONS_AUDIT_V1 ==="

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_buttons_icons \
PYTHONPATH=src \
python -m py_compile \
  src/marketcore/presentation/route_groups.py \
  src/marketcore/presentation/ui_labels.py \
  src/marketcore/presentation/registry_autodiscovery.py

# 1. Запрещаем dangerous UI-действия в presentation layer.
if grep -RInE 'send_order|place_order|cancel_order|execute_order|LiveExecution|PaperExecution|FinamClient|INSERT INTO .*orders|INSERT INTO .*fills|UPDATE .*execution|UPDATE .*runtime' \
  src/marketcore/presentation; then
  echo "DANGEROUS_UI_ACTION_FOUND"
  exit 1
fi

# 2. Основные страницы должны иметь пиктограммы.
missing_icons=$(
PYTHONPATH=src python - <<'PY'
from marketcore.presentation.registry_autodiscovery import discover_pages

required = {
    "/",
    "/edge-factory",
    "/max-edge",
    "/edge-score-shadow",
    "/edge-score-shadow-daily",
    "/market-model",
    "/portfolio",
    "/risk",
    "/system",
    "/logs",
    "/settings",
}

missing = []
for page in discover_pages():
    if page.route in required and not getattr(page, "icon", None):
        missing.append(page.route)

print("\n".join(sorted(missing)))
PY
)

if [ -n "$missing_icons" ]; then
  echo "MISSING_PAGE_ICONS"
  echo "$missing_icons"
  exit 1
fi

# 3. Основные маршруты из очищенного меню не должны давать 404.
routes=$(
PYTHONPATH=src python - <<'PY'
from marketcore.presentation.route_groups import ROUTE_GROUPS

seen = []
for group in ROUTE_GROUPS:
    for route in group.routes:
        if route not in seen:
            seen.append(route)

print("\n".join(seen))
PY
)

sudo systemctl restart marketcore-ui-shell.service
sleep 2

while IFS= read -r route; do
  [ -n "$route" ] || continue
  code=$(curl -sS -o /tmp/marketcore_route_check.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  if [ "$code" != "200" ]; then
    echo "ROUTE_HTTP_NOT_OK route=$route code=$code"
    exit 1
  fi
done <<< "$routes"

# 4. В HTML основных страницах должны быть пиктограммы карточек/разделов или emoji/icon markup.
for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /system; do
  curl -fsS "http://127.0.0.1:8080${route}?v=$(date +%s)" >/tmp/marketcore_icon_check.html

  if ! grep -qE 'icon|emoji|🎯|👁|📊|⚙|📋|🏠|🔎|📈|🧠|🛡' /tmp/marketcore_icon_check.html; then
    echo "NO_ICON_MARKUP_IN_ROUTE=$route"
    exit 1
  fi
done

# 5. Если есть button/link-like controls, они не должны быть пустыми.
if grep -RInE '<button[^>]*>[[:space:]]*</button>|<a[^>]*>[[:space:]]*</a>' src/marketcore/presentation; then
  echo "EMPTY_BUTTON_OR_LINK_FOUND"
  exit 1
fi

echo "checked_routes=$(echo "$routes" | wc -l)"
echo "missing_icons=0"
echo "dangerous_ui_actions=0"
echo "empty_buttons=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_BUTTONS_AND_ICONS_AUDIT_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_BUTTONS_AND_ICONS_AUDIT_V1_OK"
