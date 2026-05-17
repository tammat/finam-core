from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class InstitutionalExecutionDecision:
    allowed: bool
    action: str
    multiplier: float
    reason: str


class InstitutionalExecutionGate:
    """Русский комментарий: событийный institutional gate перед входом в сделку."""

    def evaluate(
        self,
        *,
        symbol: str,
        strategy: str,
        regime_ru: str,
        liquidity_score: float = 0.0,
        churn_status: str = "",
        now: datetime | None = None,
        has_cbr_event_today: bool = False,
        has_inventory_event_today: bool = False,
        minutes_to_event: int | None = None,
        is_rollover_window: bool = False,
    ) -> InstitutionalExecutionDecision:
        now = now or datetime.utcnow()
        current_time = now.time()

        symbol = str(symbol or "")
        strategy = str(strategy or "")
        regime_ru = str(regime_ru or "❔ Нет данных")
        churn_status = str(churn_status or "")

        # Русский комментарий: базовая активная сессия Мосбиржи.
        if current_time < time(7, 0) or current_time > time(23, 50):
            return InstitutionalExecutionDecision(
                allowed=False,
                action="BLOCK",
                multiplier=0.0,
                reason="вне активного торгового окна",
            )

        # Русский комментарий: фьючерсный rollover risk.
        if is_rollover_window:
            return InstitutionalExecutionDecision(
                allowed=True,
                action="REDUCE",
                multiplier=0.5,
                reason="период ролловера фьючерса: снижаем размер позиции",
            )

        # Русский комментарий: события по запасам для нефти/газа.
        if symbol.startswith(("BR", "NG")) or "BR_" in strategy or "NG_" in strategy:
            if has_inventory_event_today and minutes_to_event is not None:
                if 0 <= minutes_to_event <= 30:
                    return InstitutionalExecutionDecision(
                        allowed=False,
                        action="BLOCK",
                        multiplier=0.0,
                        reason="близко событие по запасам: вход запрещён",
                    )

                if 30 < minutes_to_event <= 90:
                    return InstitutionalExecutionDecision(
                        allowed=True,
                        action="REDUCE",
                        multiplier=0.5,
                        reason="скоро событие по запасам: снижаем размер позиции",
                    )

        # Русский комментарий: события ЦБ для валютных стратегий.
        if symbol.startswith("USDRUB") or "USDRUB" in strategy:
            if has_cbr_event_today:
                return InstitutionalExecutionDecision(
                    allowed=True,
                    action="REDUCE",
                    multiplier=0.5,
                    reason="день заседания ЦБ: снижаем размер позиции",
                )

        # Русский комментарий: высокий churn ограничивает стратегию.
        if "Критический churn" in churn_status:
            return InstitutionalExecutionDecision(
                allowed=False,
                action="BLOCK",
                multiplier=0.0,
                reason="критический churn: стратегия создаёт слишком много сделок",
            )

        if "Высокий churn" in churn_status:
            return InstitutionalExecutionDecision(
                allowed=True,
                action="REDUCE",
                multiplier=0.5,
                reason="высокий churn: снижаем размер позиции",
            )

        # Русский комментарий: режимы крупного капитала.
        if regime_ru == "🪤 Ловушка пробоя" and "BREAKOUT" in strategy:
            return InstitutionalExecutionDecision(
                allowed=False,
                action="BLOCK",
                multiplier=0.0,
                reason="ловушка пробоя: breakout-вход запрещён",
            )

        if regime_ru == "⚪ Обычная активность":
            return InstitutionalExecutionDecision(
                allowed=True,
                action="REDUCE",
                multiplier=0.75,
                reason="обычная активность крупного капитала: снижаем агрессивность",
            )

        if regime_ru in {"🟢 Накопление", "🚀 Запуск тренда"}:
            return InstitutionalExecutionDecision(
                allowed=True,
                action="ALLOW",
                multiplier=1.0,
                reason=f"режим допускает вход: {regime_ru}",
            )

        if liquidity_score < 0.05:
            return InstitutionalExecutionDecision(
                allowed=True,
                action="REDUCE",
                multiplier=0.5,
                reason="низкая оценка ликвидности: снижаем размер позиции",
            )

        return InstitutionalExecutionDecision(
            allowed=True,
            action="ALLOW",
            multiplier=1.0,
            reason="ограничений institutional gate не выявлено",
        )
