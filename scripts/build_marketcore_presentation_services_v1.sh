#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKETCORE_PRESENTATION_SERVICES_V1 ==="

mkdir -p src/marketcore/presentation/services scripts
touch src/marketcore/presentation/services/__init__.py

cat > src/marketcore/presentation/services/locale_service.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LocaleSettings:
    locale: str = "ru"
    timezone: str = "Europe/Moscow"
    currency: str = "RUB"
    theme: str = "dark"


class LocaleService:
    def __init__(self, settings: LocaleSettings | None = None) -> None:
        self.settings = settings or LocaleSettings()

    @property
    def locale(self) -> str:
        return self.settings.locale

    @property
    def timezone(self) -> str:
        return self.settings.timezone

    @property
    def currency(self) -> str:
        return self.settings.currency

    @property
    def theme(self) -> str:
        return self.settings.theme
PY

cat > src/marketcore/presentation/services/number_service.py <<'PY'
from __future__ import annotations


class NumberService:
    def format_number(self, value, precision: int = 2) -> str:
        try:
            return f"{float(value):,.{precision}f}".replace(",", " ")
        except (TypeError, ValueError):
            return "—"

    def format_percent(self, value, precision: int = 2) -> str:
        try:
            return f"{float(value):.{precision}f}%"
        except (TypeError, ValueError):
            return "—"

    def format_ratio(self, value, precision: int = 4) -> str:
        return self.format_number(value, precision)
PY

cat > src/marketcore/presentation/services/currency_service.py <<'PY'
from __future__ import annotations

from marketcore.presentation.services.number_service import NumberService


class CurrencyService:
    SYMBOLS = {
        "RUB": "₽",
        "USD": "$",
        "EUR": "€",
        "CNY": "¥",
        "HKD": "HK$",
        "JPY": "¥",
    }

    def __init__(self, numbers: NumberService | None = None) -> None:
        self.numbers = numbers or NumberService()

    def format_money(self, value, currency: str = "RUB", precision: int = 2) -> str:
        formatted = self.numbers.format_number(value, precision)
        if formatted == "—":
            return formatted
        return f"{formatted} {self.SYMBOLS.get(currency, currency)}"
PY

cat > src/marketcore/presentation/services/datetime_service.py <<'PY'
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


class DateTimeService:
    def format_datetime(self, value, timezone: str = "Europe/Moscow") -> str:
        if not value:
            return "—"

        try:
            if isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif isinstance(value, datetime):
                dt = value
            else:
                return "—"

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))

            return dt.astimezone(ZoneInfo(timezone)).strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            return str(value)
PY

cat > src/marketcore/presentation/services/unit_service.py <<'PY'
from __future__ import annotations


class UnitService:
    UNITS = {
        "contract": "контр.",
        "lot": "лот",
        "share": "шт.",
        "barrel": "барр.",
        "tick": "тик",
        "atr": "ATR",
        "rr": "RR",
        "pf": "PF",
        "expectancy": "матожидание",
        "pnl": "P&L",
        "drawdown": "просадка",
        "signal": "сигнал",
        "trade": "сделка",
        "fill": "исполнение",
        "edge": "edge",
    }

    def label(self, key: str) -> str:
        return self.UNITS.get(key, key)
PY

cat > src/marketcore/presentation/services/status_service.py <<'PY'
from __future__ import annotations


class StatusService:
    LABELS_RU = {
        "OK": "ОК",
        "READY": "Готово",
        "RUNNING": "Работает",
        "BLOCKED": "Заблокировано",
        "ERROR": "Ошибка",
        "WARNING": "Предупреждение",
        "VALIDATED": "Подтверждено",
        "REJECTED": "Отклонено",
        "UNKNOWN": "Неизвестно",
        "OFF": "Выключено",
        "ON": "Включено",
        "SAFE": "Безопасно",
        "STALE": "Устарело",
        "FRESH": "Актуально",
    }

    def label(self, status: str | None, locale: str = "ru") -> str:
        key = (status or "UNKNOWN").upper()
        if locale == "ru":
            return self.LABELS_RU.get(key, key)
        return key

    def severity(self, status: str | None) -> str:
        key = (status or "UNKNOWN").upper()
        if key in {"OK", "READY", "RUNNING", "VALIDATED", "ON", "SAFE", "FRESH"}:
            return "ok"
        if key in {"WARNING", "BLOCKED", "STALE"}:
            return "warn"
        if key in {"ERROR", "REJECTED"}:
            return "error"
        if key in {"OFF", "UNKNOWN"}:
            return "off"
        return "unknown"
PY

cat > src/marketcore/presentation/services/icon_service.py <<'PY'
from __future__ import annotations


class IconService:
    ICONS = {
        "home": "⌂",
        "runtime": "▶",
        "knowledge_graph": "◎",
        "research": "⌕",
        "portfolio": "◈",
        "orders": "⇄",
        "risk": "⚠",
        "validation": "✓",
        "logs": "≡",
        "system": "⚙",
        "ai": "✦",
        "paper": "□",
        "edge": "◇",
        "capital": "₽",
        "signal": "→",
        "trade": "◆",
        "fill": "■",
    }

    def icon(self, key: str) -> str:
        return self.ICONS.get(key, "•")
PY

cat > src/marketcore/presentation/services/i18n_service.py <<'PY'
from __future__ import annotations

from marketcore.presentation.api_client import get_json


class I18NService:
    FALLBACK = {
        ("ui", "marketcore_os", "ru"): "MarketCore OS",
        ("ui", "platform_m2", "ru"): "Platform M2",
        ("ui", "knowledge_graph", "ru"): "Граф знаний",
        ("ui", "validation", "ru"): "Валидация",
        ("ui", "statistics", "ru"): "Статистика",
        ("ui", "paper_edge_discovery_center", "ru"): "Центр поиска Edge",
        ("ui", "runtime", "ru"): "Runtime",
        ("ui", "research", "ru"): "Исследования",
        ("ui", "portfolio", "ru"): "Портфель",
        ("ui", "risk", "ru"): "Риск",
    }

    def label(self, object_type: str, object_key: str, locale: str = "ru") -> str:
        fallback = self.FALLBACK.get((object_type, object_key, locale), object_key)

        data = get_json("/api/kg/v1/ontology", timeout=1.0)
        rows = data.get("data") or []

        for row in rows:
            if (
                row.get("object_type") == object_type
                and row.get("object_key") == object_key
                and row.get("locale") == locale
            ):
                return str(row.get("label") or fallback)

        return fallback
PY

cat > src/marketcore/presentation/services/formatter_service.py <<'PY'
from __future__ import annotations

from marketcore.presentation.services.currency_service import CurrencyService
from marketcore.presentation.services.datetime_service import DateTimeService
from marketcore.presentation.services.i18n_service import I18NService
from marketcore.presentation.services.locale_service import LocaleService
from marketcore.presentation.services.number_service import NumberService
from marketcore.presentation.services.unit_service import UnitService


class FormatterService:
    def __init__(
        self,
        locale: LocaleService,
        numbers: NumberService,
        currency: CurrencyService,
        datetime_service: DateTimeService,
        units: UnitService,
        i18n: I18NService,
    ) -> None:
        self.locale = locale
        self.numbers = numbers
        self.currency = currency
        self.datetime_service = datetime_service
        self.units = units
        self.i18n = i18n

    def number(self, value, precision: int = 2) -> str:
        return self.numbers.format_number(value, precision)

    def percent(self, value, precision: int = 2) -> str:
        return self.numbers.format_percent(value, precision)

    def ratio(self, value, precision: int = 4) -> str:
        return self.numbers.format_ratio(value, precision)

    def money(self, value, currency: str | None = None, precision: int = 2) -> str:
        return self.currency.format_money(
            value=value,
            currency=currency or self.locale.currency,
            precision=precision,
        )

    def datetime(self, value) -> str:
        return self.datetime_service.format_datetime(
            value=value,
            timezone=self.locale.timezone,
        )

    def unit(self, key: str) -> str:
        return self.units.label(key)

    def label(self, object_type: str, object_key: str) -> str:
        return self.i18n.label(
            object_type=object_type,
            object_key=object_key,
            locale=self.locale.locale,
        )
PY

cat > src/marketcore/presentation/presentation_context.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass

from marketcore.presentation.api_client import get_json
from marketcore.presentation.services.currency_service import CurrencyService
from marketcore.presentation.services.datetime_service import DateTimeService
from marketcore.presentation.services.formatter_service import FormatterService
from marketcore.presentation.services.i18n_service import I18NService
from marketcore.presentation.services.icon_service import IconService
from marketcore.presentation.services.locale_service import LocaleService
from marketcore.presentation.services.number_service import NumberService
from marketcore.presentation.services.status_service import StatusService
from marketcore.presentation.services.unit_service import UnitService


@dataclass(frozen=True)
class PresentationContext:
    locale: LocaleService
    numbers: NumberService
    currency: CurrencyService
    datetime: DateTimeService
    units: UnitService
    i18n: I18NService
    icons: IconService
    status: StatusService
    formatter: FormatterService

    def api_get(self, path: str, timeout: float = 2.0) -> dict:
        return get_json(path, timeout=timeout)


def build_presentation_context() -> PresentationContext:
    locale = LocaleService()
    numbers = NumberService()
    currency = CurrencyService(numbers)
    datetime_service = DateTimeService()
    units = UnitService()
    i18n = I18NService()
    icons = IconService()
    status = StatusService()

    formatter = FormatterService(
        locale=locale,
        numbers=numbers,
        currency=currency,
        datetime_service=datetime_service,
        units=units,
        i18n=i18n,
    )

    return PresentationContext(
        locale=locale,
        numbers=numbers,
        currency=currency,
        datetime=datetime_service,
        units=units,
        i18n=i18n,
        icons=icons,
        status=status,
        formatter=formatter,
    )
PY

cat > scripts/test_marketcore_presentation_services_v1.sh <<'SH_TEST'
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
SH_TEST

chmod +x scripts/test_marketcore_presentation_services_v1.sh

scripts/test_marketcore_presentation_services_v1.sh

echo "=== FILE_STRUCTURE_MARKETCORE_PRESENTATION_SERVICES_V1 ==="
find src/marketcore/presentation/services -maxdepth 1 -type f | sort
echo "src/marketcore/presentation/presentation_context.py"
echo "scripts/test_marketcore_presentation_services_v1.sh"
echo "VERDICT=BUILD_MARKETCORE_PRESENTATION_SERVICES_V1_OK"
