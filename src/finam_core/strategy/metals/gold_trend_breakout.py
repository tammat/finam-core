from __future__ import annotations


class GoldTrendBreakout:
    """Адаптер отдельной трендово-пробойной модели золота.

    До подтверждения стакана модель остаётся research-only и не получает V4
    Paper admission.
    """

    def on_quote(self, state: dict):
        return None
