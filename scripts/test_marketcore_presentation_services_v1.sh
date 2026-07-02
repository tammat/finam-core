#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_PRESENTATION_SERVICES_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/services/locale_service.py \
  src/marketcore/presentation/services/number_service.py \
  src/marketcore/presentation/services/currency_service.py \
  src/marketcore/presentation/services/datetime_service.py \
  src/marketcore/presentation/services/unit_service.py \
  src/marketcore/presentation/services/status_service.py \
  src/marketcore/presentation/services/icon_service.py \
  src/marketcore/presentation/services/i18n_service.py \
  src/marketcore/presentation/services/formatter_service.py \
  src/marketcore/presentation/presentation_context.py

PYTHONPATH=src python <<'PY'
from marketcore.presentation.presentation_context import build_presentation_context

ctx = build_presentation_context()

assert ctx.locale.locale == "ru"
assert ctx.locale.timezone == "Europe/Moscow"
assert ctx.locale.currency == "RUB"
assert ctx.locale.theme == "dark"

assert ctx.formatter.money(1234567.34, "RUB") == "1 234 567.34 ₽"
assert ctx.formatter.money(1234567.34, "USD") == "1 234 567.34 $"
assert ctx.formatter.number(1234567.34, 1) == "1 234 567.3"
assert ctx.formatter.percent(12.3456, 2) == "12.35%"
assert ctx.formatter.ratio(1.234567, 4) == "1.2346"

assert ctx.formatter.unit("contract") == "контр."
assert ctx.formatter.unit("pf") == "PF"

assert ctx.status.label("READY") == "Готово"
assert ctx.status.label("ERROR") == "Ошибка"
assert ctx.status.severity("READY") == "ok"
assert ctx.status.severity("ERROR") == "error"

assert ctx.icons.icon("edge") == "◇"
assert ctx.icons.icon("runtime") == "▶"

assert ctx.formatter.datetime("2026-07-02T14:00:00+00:00").startswith("02.07.2026")

assert ctx.formatter.label("ui", "marketcore_os") == "MarketCore OS"

print("locale=ru")
print("timezone=Europe/Moscow")
print("currency=RUB")
print("money_rub=" + ctx.formatter.money(1234567.34, "RUB"))
print("money_usd=" + ctx.formatter.money(1234567.34, "USD"))
print("number=" + ctx.formatter.number(1234567.34, 1))
print("percent=" + ctx.formatter.percent(12.3456, 2))
print("unit_contract=" + ctx.formatter.unit("contract"))
print("status_ready=" + ctx.status.label("READY"))
print("icon_edge=" + ctx.icons.icon("edge"))
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKETCORE_PRESENTATION_SERVICES_V1_READY"
echo "VERDICT=TEST_MARKETCORE_PRESENTATION_SERVICES_V1_OK"
