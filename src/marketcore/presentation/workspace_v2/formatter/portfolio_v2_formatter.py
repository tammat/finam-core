from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from marketcore.presentation.services.operator_settings_v1 import OperatorSettingsV1


class PortfolioV2Formatter:
    def __init__(self, settings: OperatorSettingsV1 | None = None) -> None:
        self._settings = settings or OperatorSettingsV1.load()
    MONEY_KEYWORDS = (
        "цена",
        "стоимость",
        "сумма",
        "p&l",
        "pnl",
        "прибыль",
        "убыток",
        "результат",
        "оценка",
    )

    PERCENT_KEYWORDS = (
        "_pct",
        "pct",
        "percent",
        "процент",
        "доля",
        "yield",
        "%",
        "change",
    )

    @staticmethod
    def source_key(source_view: str) -> str:
        normalized = source_view.replace(".", "_").lower()
        return f"portfolio.source.{normalized}"

    @staticmethod
    def column_key(column_name: str) -> str:
        normalized = column_name.lower()
        return f"portfolio.column.{normalized}"

    @staticmethod
    def card_id(source_view: str, index: int) -> str:
        normalized = source_view.replace(".", "_").lower()
        return f"portfolio.card.{normalized}.{index}"

    @staticmethod
    def section_id(section_code: str) -> str:
        return f"portfolio.section.{section_code.lower()}"

    def value(self, column_name: str, value: Any) -> str:
        if value is None:
            return "—"

        if isinstance(value, datetime):
            dt = value if value.tzinfo is not None else value.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(ZoneInfo(self._settings.timezone)).strftime("%d.%m.%Y, %H:%M")

        text_value = str(value).strip()
        if not text_value:
            return "—"

        decimal_value = self._try_decimal(text_value)
        if decimal_value is None:
            return text_value

        column = column_name.lower()

        if any(marker in column for marker in self.PERCENT_KEYWORDS):
            return self._format_decimal(decimal_value) + "%"

        if any(marker in column for marker in self.MONEY_KEYWORDS):
            return self._format_decimal(decimal_value) + " " + self._currency_symbol()

        return self._format_decimal(decimal_value)

    @staticmethod
    def _currency_symbol() -> str:
        # Источник v_real_portfolio_summary_ru номинирован в RUB.
        # Не переименовываем валюту без доказанного FX-преобразования.
        return "₽"

    @staticmethod
    def _try_decimal(value: str) -> Decimal | None:
        try:
            return Decimal(value.replace(",", "."))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        quantized = value.quantize(Decimal("0.01"))
        sign = "-" if quantized < 0 else ""
        abs_text = f"{abs(quantized):.2f}"
        whole, frac = abs_text.split(".")
        grouped = f"{int(whole):,}".replace(",", " ")
        return f"{sign}{grouped},{frac}"
