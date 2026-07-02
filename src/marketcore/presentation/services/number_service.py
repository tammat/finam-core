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
