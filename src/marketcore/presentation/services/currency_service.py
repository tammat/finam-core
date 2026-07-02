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
