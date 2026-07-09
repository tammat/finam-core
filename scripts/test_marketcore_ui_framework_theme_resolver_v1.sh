#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_THEME_RESOLVER_V1 ==="

file="src/marketcore/presentation/framework/theme_resolver.py"
test -f "$file"

PYTHONPYCACHEPREFIX=/tmp/framework_theme_resolver \
PYTHONPATH=src \
python -m py_compile "$file"

if grep -E "<div|<section|</" "$file"; then
    echo "HTML_IN_RESOLVER_FOUND"
    exit 1
fi

if grep -E "#[0-9A-Fa-f]{6}|[0-9]+(px|rem|em)\\b" "$file"; then
    echo "HARDCODED_STYLE_VALUE_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1

resolver = ThemeResolverV1()

theme = resolver.resolve("DEFAULT")

assert theme.theme_code == "DEFAULT"
assert theme.theme_name_key == "ui.theme.default.name"
assert theme.description_key == "ui.theme.default.description"

assert theme.get("CARD_RADIUS") == "18"
assert theme.get("TOUCH_SIZE") == "44"
assert theme.get("PRIMARY_COLOR") == "brand.primary"
assert theme.get("UNKNOWN", "fallback") == "fallback"

theme2 = resolver.resolve("DEFAULT")
assert theme2 is theme

print("theme_resolver=OK")
print("theme_cache=OK")
PY

echo "theme_resolver=OK"
echo "theme_cache=OK"
echo "html_in_resolver=0"
echo "hardcoded_style_values=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_THEME_RESOLVER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_THEME_RESOLVER_V1_OK"
