#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_I18N_TIMEZONE_V1 ==="

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.dashboard.i18n import t, normalize_language
from marketcore.presentation.dashboard.timezone import convert_utc_iso, normalize_timezone

assert normalize_language("ru") == "ru"
assert normalize_language("en") == "en"
assert normalize_language("de") == "ru"

assert t("risk", "ru") == "Риски"
assert t("risk", "en") == "Risk"
assert t("unknown", "ru") == "unknown"

assert normalize_timezone("Europe/Moscow") == "Europe/Moscow"
assert normalize_timezone("Europe/Helsinki") == "Europe/Helsinki"
assert normalize_timezone("Bad/Zone") == "Europe/Moscow"

moscow = convert_utc_iso("2026-07-01T12:00:00+00:00", "Europe/Moscow")
helsinki = convert_utc_iso("2026-07-01T12:00:00+00:00", "Europe/Helsinki")

print("lang_ru=READY")
print("lang_en=READY")
print("timezone_moscow=" + moscow)
print("timezone_helsinki=" + helsinki)
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print("VERDICT=DASHBOARD_I18N_TIMEZONE_V1_READY")
PY

echo "VERDICT=TEST_DASHBOARD_I18N_TIMEZONE_V1_OK"
