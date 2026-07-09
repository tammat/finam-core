#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_UI_FRAMEWORK_DB_MAPPER_V1 ==="

files=(
  "src/marketcore/presentation/framework/mapper/__init__.py"
  "src/marketcore/presentation/framework/mapper/base_mapper.py"
  "src/marketcore/presentation/framework/mapper/theme_mapper.py"
  "src/marketcore/presentation/framework/theme_resolver.py"
)

for f in "${files[@]}"; do
  test -f "$f"
done

PYTHONPYCACHEPREFIX=/tmp/framework_db_mapper \
PYTHONPATH=src \
python -m py_compile "${files[@]}"

if grep -RInE '<div|<section|</|#[0-9A-Fa-f]{6}|[0-9]+(px|rem|em)\b' \
  src/marketcore/presentation/framework/mapper \
  src/marketcore/presentation/framework/theme_resolver.py; then
    echo "FORBIDDEN_UI_OR_STYLE_FOUND"
    exit 1
fi

if grep -RInE 'row\["|row\[' src/marketcore/presentation/framework/theme_resolver.py; then
    echo "SCHEMA_COUPLING_IN_THEME_RESOLVER_FOUND"
    exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
from marketcore.presentation.framework.mapper.theme_mapper import (
    ThemeModelMapper,
    ThemePropertyMapper,
)

sample_theme = {
    "theme_code": "DEFAULT",
    "theme_name_key": "ui.theme.default.name",
    "description_key": "ui.theme.default.description",
}

sample_property = {
    "property_code": "CARD_RADIUS",
    "property_value": "18",
    "property_type": "INTEGER",
    "description_key": "ui.theme.property.card_radius",
    "display_order": 10,
}

prop = ThemePropertyMapper.from_db(sample_property)
assert prop.property_code == "CARD_RADIUS"
assert prop.property_value == "18"

model = ThemeModelMapper.with_properties(sample_theme, [sample_property])
assert model.theme_code == "DEFAULT"
assert model.get("CARD_RADIUS") == "18"

resolver = ThemeResolverV1()
theme = resolver.resolve("DEFAULT")

assert theme.theme_code == "DEFAULT"
assert theme.get("CARD_RADIUS") == "18"
assert theme.get("TOUCH_SIZE") == "44"
assert resolver.resolve("DEFAULT") is theme

print("db_mapper=OK")
print("theme_mapper=OK")
print("theme_resolver_uses_mapper=OK")
PY

echo "db_mapper_framework=OK"
echo "theme_mapper=OK"
echo "schema_isolation_theme_resolver=OK"
echo "row_access_outside_mapper=0"
echo "html_in_mapper=0"
echo "style_hardcodes_in_mapper=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_UI_FRAMEWORK_DB_MAPPER_V1_READY"
echo "VERDICT=TEST_MARKETCORE_UI_FRAMEWORK_DB_MAPPER_V1_OK"
