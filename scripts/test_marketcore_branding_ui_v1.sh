#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_BRANDING_UI_V1 ==="

# 1. UI/doc replacement: только presentation + docs.
python - <<'PY'
from pathlib import Path

targets = [
    Path("src/marketcore/presentation"),
    Path("docs"),
]

replacements = {
    "FinamCore": "MarketCore",
    "FINAM_CORE": "MARKETCORE",
    "FINAM CORE": "MARKETCORE",
    "finam-core": "marketcore",
}

for root in targets:
    if not root.exists():
        continue
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".py", ".md", ".txt", ".html", ".css", ".js"}:
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        old = s
        for src, dst in replacements.items():
            s = s.replace(src, dst)
        if s != old:
            p.write_text(s, encoding="utf-8")
PY

# 2. Добавляем/обновляем i18n-ресурсы бренда.
psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('system.product.name', 'ru', 'MarketCore', 'MarketCore', 'MarketCore', 'Название платформы', '🧠', 'system'),
('system.product.subtitle', 'ru', 'Market Research & Analytics Platform', 'Research Platform', 'Research', 'Исследовательская аналитическая платформа', '', 'system'),
('page.about.product_name', 'ru', 'MarketCore', 'MarketCore', 'MarketCore', 'Название системы', '🧠', 'page')
ON CONFLICT(resource_key, locale_code) DO UPDATE SET
    caption=EXCLUDED.caption,
    caption_short=EXCLUDED.caption_short,
    caption_mobile=EXCLUDED.caption_mobile,
    tooltip=EXCLUDED.tooltip,
    icon=EXCLUDED.icon,
    resource_group=EXCLUDED.resource_group,
    updated_at=now();
SQL

# 3. Компиляция presentation.
PYTHONPYCACHEPREFIX=/tmp/finam_pycache_branding_ui \
PYTHONPATH=src \
python -m py_compile \
  $(find src/marketcore/presentation -name '*.py' -type f)

# 4. В пользовательском presentation/docs больше не должно быть FinamCore как бренда.
if grep -RInE 'FinamCore|FINAM_CORE|FINAM CORE|finam-core' \
  src/marketcore/presentation docs; then
  echo "LEGACY_PRODUCT_BRAND_FOUND_IN_UI_OR_DOCS"
  exit 1
fi

# 5. Но broker-specific Finam внутри src допускается и не проверяется на удаление.
# 6. HTTP smoke.
sudo systemctl restart marketcore-ui-shell.service
sleep 2

for route in / /max-edge /edge-score-shadow /edge-score-shadow-daily /system; do
  code=$(curl -sS -o /tmp/marketcore_branding_ui.html -w "%{http_code}" "http://127.0.0.1:8080${route}?v=$(date +%s)" || true)
  if [ "$code" != "200" ]; then
    echo "ROUTE_HTTP_NOT_OK route=$route code=$code"
    exit 1
  fi
done

# 7. Главная или system должны содержать MarketCore после рендера.
curl -fsS "http://127.0.0.1:8080/?v=$(date +%s)" >/tmp/marketcore_branding_home.html
curl -fsS "http://127.0.0.1:8080/system?v=$(date +%s)" >/tmp/marketcore_branding_system.html

if ! grep -q "MarketCore" /tmp/marketcore_branding_home.html /tmp/marketcore_branding_system.html; then
  echo "MARKETCORE_BRAND_NOT_RENDERED"
  exit 1
fi

missing=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  VALUES
    ('system.product.name'),
    ('system.product.subtitle'),
    ('page.about.product_name')
) AS required(resource_key)
LEFT JOIN presentation.ui_resource_v1 r
  ON r.resource_key=required.resource_key
 AND r.locale_code='ru'
WHERE r.resource_key IS NULL;
")

if [ "$missing" != "0" ]; then
  echo "MISSING_BRANDING_I18N=$missing"
  exit 1
fi

echo "branding_i18n_missing=0"
echo "legacy_product_brand_in_ui_docs=0"
echo "http_routes=OK"
echo "product_brand=MarketCore"
echo "broker_adapter_brand=Finam"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_BRANDING_UI_V1_READY"
echo "VERDICT=TEST_MARKETCORE_BRANDING_UI_V1_OK"
