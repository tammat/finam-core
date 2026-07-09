from __future__ import annotations


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
