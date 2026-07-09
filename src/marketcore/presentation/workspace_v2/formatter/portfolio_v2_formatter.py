from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class PortfolioV2Formatter:
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

    @classmethod
    def value(cls, column_name: str, value: Any) -> str:
        if value is None:
            return "—"

        text_value = str(value).strip()
        if not text_value:
            return "—"

        decimal_value = cls._try_decimal(text_value)
        if decimal_value is None:
            return text_value

        column = column_name.lower()

        if any(marker in column for marker in cls.PERCENT_KEYWORDS):
            return cls._format_decimal(decimal_value) + "%"

        if any(marker in column for marker in cls.MONEY_KEYWORDS):
            return cls._format_decimal(decimal_value) + " ₽"

        return cls._format_decimal(decimal_value)

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
