from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class PortfolioV2Formatter:
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

    @staticmethod
    def value(value: Any) -> str:
        if value is None:
            return "—"

        if isinstance(value, bool):
            return "1" if value else "0"

        if isinstance(value, int):
            return str(value)

        if isinstance(value, float):
            return PortfolioV2Formatter._decimal_to_text(Decimal(str(value)))

        if isinstance(value, Decimal):
            return PortfolioV2Formatter._decimal_to_text(value)

        text = str(value).strip()
        if not text:
            return "—"

        try:
            return PortfolioV2Formatter._decimal_to_text(Decimal(text))
        except (InvalidOperation, ValueError):
            return text

    @staticmethod
    def _decimal_to_text(value: Decimal) -> str:
        quantized = value.quantize(Decimal("0.01"))
        return format(quantized, "f")
