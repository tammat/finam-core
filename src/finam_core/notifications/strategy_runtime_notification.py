from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyRuntimeNotification:
    symbol: str
    strategy: str
    status: str
    allow_trade: bool
    watch_only: bool
    risk_multiplier: float
    reason: str


class StrategyRuntimeNotificationFormatter:
    """Русский комментарий: формирует русские Telegram/Grafana-сообщения по runtime control."""

    def format_telegram(self, event: StrategyRuntimeNotification) -> str:
        trade_status = "разрешена" if event.allow_trade else "запрещена"
        watch_status = "да" if event.watch_only else "нет"

        return (
            "⚙️ Обновлён режим стратегии\n\n"
            f"Инструмент: {event.symbol}\n"
            f"Стратегия: {event.strategy}\n"
            f"Решение: {event.status}\n"
            f"Торговля: {trade_status}\n"
            f"Режим наблюдения: {watch_status}\n"
            f"Риск-мультипликатор: {event.risk_multiplier:.2f}\n"
            f"Причина: {event.reason}"
        )

    def format_grafana_annotation(self, event: StrategyRuntimeNotification) -> dict:
        return {
            "title": "Обновлён режим стратегии",
            "text": self.format_telegram(event),
            "tags": [
                "стратегия",
                "runtime-control",
                str(event.status),
                str(event.symbol),
                str(event.strategy),
            ],
        }
