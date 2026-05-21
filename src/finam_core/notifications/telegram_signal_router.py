from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramSignalRoute:
    channel_type: str
    should_send: bool
    target_env: str
    reason: str


THRESHOLDS = {
    "REAL": 0.0,
    "RISK": 0.0,
    "REVIEW": 0.0,
    "PAPER": 0.70,
    "RADAR": 0.60,
}


TARGET_ENV_BY_CHANNEL = {
    "REAL": "TELEGRAM_REAL_DESK_CHAT_ID",
    "RISK": "TELEGRAM_REAL_DESK_CHAT_ID",
    "REVIEW": "TELEGRAM_REAL_DESK_CHAT_ID",
    "PAPER": "TELEGRAM_PAPER_LAB_CHAT_ID",
    "RADAR": "TELEGRAM_MARKET_RADAR_CHAT_ID",
}


def route_telegram_signal(
    *,
    channel_type: str,
    confidence: float,
) -> TelegramSignalRoute:
    """
    Русский комментарий:
    Решает, отправлять ли Telegram-сообщение и в какой канал.
    """

    channel = str(channel_type).strip().upper()
    score = float(confidence)

    threshold = THRESHOLDS.get(channel)
    target_env = TARGET_ENV_BY_CHANNEL.get(channel, "TELEGRAM_DEFAULT_CHAT_ID")

    if threshold is None:
        return TelegramSignalRoute(
            channel_type=channel,
            should_send=False,
            target_env=target_env,
            reason="неизвестный_тип_сообщения",
        )

    if score < threshold:
        return TelegramSignalRoute(
            channel_type=channel,
            should_send=False,
            target_env=target_env,
            reason=f"уверенность_ниже_порога:{score}<{threshold}",
        )

    return TelegramSignalRoute(
        channel_type=channel,
        should_send=True,
        target_env=target_env,
        reason="сообщение_допущено_к_отправке",
    )
