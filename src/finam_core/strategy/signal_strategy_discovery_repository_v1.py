from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any


class SignalStrategyDiscoveryRepositoryV1:
    """
    Русский комментарий:
    Репозиторий сохраняет сигналы, по которым стратегия не была определена.

    Это не торговый слой и не execution.
    Назначение — не дать системе молча создать сделку без strategy/timeframe,
    а вынести неизвестный сигнал на разбор и последующее проектирование стратегии.
    """

    def __init__(self, conn: Any) -> None:
        self.conn = conn

    def record_unresolved_signal(
        self,
        *,
        symbol: str,
        reason: str,
        source: str,
        payload: dict[str, Any] | None,
        proposed_strategy: str | None = None,
        proposed_timeframe: str | None = None,
        proposed_continuous_symbol: str | None = None,
    ) -> int:
        payload = payload or {}

        with self.conn.cursor() as cur:
            cur.execute(
                """
                insert into signal_strategy_discovery_events (
                    symbol,
                    reason,
                    source,
                    payload,
                    status,
                    proposed_strategy,
                    proposed_timeframe,
                    proposed_continuous_symbol
                )
                values (
                    %(symbol)s,
                    %(reason)s,
                    %(source)s,
                    %(payload)s::jsonb,
                    'NEW',
                    %(proposed_strategy)s,
                    %(proposed_timeframe)s,
                    %(proposed_continuous_symbol)s
                )
                returning id;
                """,
                {
                    "symbol": symbol,
                    "reason": reason,
                    "source": source,
                    "payload": json.dumps(payload, ensure_ascii=False, default=str),
                    "proposed_strategy": proposed_strategy,
                    "proposed_timeframe": proposed_timeframe,
                    "proposed_continuous_symbol": proposed_continuous_symbol,
                },
            )
            row = cur.fetchone()

        event_id = int(row[0])
        return event_id


def build_unresolved_signal_notification_v1(
    *,
    event_id: int,
    symbol: str,
    decision: Any,
    payload: dict[str, Any] | None,
) -> str:
    """
    Русский комментарий:
    Формируем короткое machine-readable уведомление для логов/Telegram-слоя.
    В Telegram пока не отправляем: этот этап только создаёт событие и текст уведомления.
    """

    payload = payload or {}

    reason = getattr(decision, "reason", "SIGNAL_STRATEGY_UNRESOLVED")
    source = getattr(decision, "source", "unknown")
    continuous_symbol = getattr(decision, "continuous_symbol", None)

    return (
        "SIGNAL_STRATEGY_UNRESOLVED_NOTIFY_REQUIRED "
        f"event_id={event_id} "
        f"symbol={symbol} "
        f"reason={reason} "
        f"source={source} "
        f"continuous_symbol={continuous_symbol} "
        f"payload_keys={','.join(sorted(payload.keys()))}"
    )


def decision_to_payload_v1(decision: Any, payload: dict[str, Any] | None) -> dict[str, Any]:
    """
    Русский комментарий:
    Сохраняем в discovery event как исходный payload, так и решение gate.
    Это нужно, чтобы потом разбирать сигнал и проектировать новую стратегию.
    """

    base = dict(payload or {})

    try:
        decision_dict = asdict(decision)
    except Exception:
        decision_dict = {
            "allowed": getattr(decision, "allowed", None),
            "strategy": getattr(decision, "strategy", None),
            "timeframe": getattr(decision, "timeframe", None),
            "continuous_symbol": getattr(decision, "continuous_symbol", None),
            "reason": getattr(decision, "reason", None),
            "source": getattr(decision, "source", None),
            "discovery_required": getattr(decision, "discovery_required", None),
        }

    base["_strategy_attribution_decision_v1"] = decision_dict
    return base
