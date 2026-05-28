from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationDedupDecisionV1:
    allowed: bool
    reason: str
    cache_key: str
    cooldown_sec: float
    elapsed_sec: float | None


class NotificationDedupCacheV1:
    """
    Русский комментарий:
    In-memory anti-spam cache для уведомлений.
    Не пишет в БД. Не отправляет сообщения.
    """

    DEFAULT_COOLDOWNS = {
        "CRITICAL": 0.0,
        "WARNING": 300.0,
        "INFO": 900.0,
        "NORMAL": 1800.0,
    }

    def __init__(self, cooldowns: dict[str, float] | None = None) -> None:
        self.cooldowns = dict(self.DEFAULT_COOLDOWNS)
        if cooldowns:
            self.cooldowns.update(cooldowns)

        self._last_sent_ts: dict[str, float] = {}

    def allows(
        self,
        *,
        category: str,
        severity: str,
        symbol: str,
        title: str,
        now_ts: float | None = None,
    ) -> NotificationDedupDecisionV1:
        now_ts = float(now_ts if now_ts is not None else time.time())
        severity = str(severity or "NORMAL")
        cache_key = self._cache_key(
            category=category,
            severity=severity,
            symbol=symbol,
            title=title,
        )

        cooldown_sec = float(self.cooldowns.get(severity, self.cooldowns["NORMAL"]))

        if cooldown_sec <= 0:
            self._last_sent_ts[cache_key] = now_ts
            return NotificationDedupDecisionV1(
                allowed=True,
                reason="bypass_cooldown",
                cache_key=cache_key,
                cooldown_sec=cooldown_sec,
                elapsed_sec=None,
            )

        last_ts = self._last_sent_ts.get(cache_key)
        if last_ts is None:
            self._last_sent_ts[cache_key] = now_ts
            return NotificationDedupDecisionV1(
                allowed=True,
                reason="first_seen",
                cache_key=cache_key,
                cooldown_sec=cooldown_sec,
                elapsed_sec=None,
            )

        elapsed = now_ts - float(last_ts)

        if elapsed >= cooldown_sec:
            self._last_sent_ts[cache_key] = now_ts
            return NotificationDedupDecisionV1(
                allowed=True,
                reason="cooldown_elapsed",
                cache_key=cache_key,
                cooldown_sec=cooldown_sec,
                elapsed_sec=elapsed,
            )

        return NotificationDedupDecisionV1(
            allowed=False,
            reason="dedup_cooldown_active",
            cache_key=cache_key,
            cooldown_sec=cooldown_sec,
            elapsed_sec=elapsed,
        )

    @staticmethod
    def _cache_key(
        *,
        category: str,
        severity: str,
        symbol: str,
        title: str,
    ) -> str:
        return "|".join(
            [
                str(category or "UNKNOWN"),
                str(severity or "NORMAL"),
                str(symbol or "UNKNOWN"),
                str(title or "").strip(),
            ]
        )
