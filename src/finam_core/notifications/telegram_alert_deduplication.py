from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass(frozen=True)
class TelegramAlertDedupDecision:
    should_send: bool
    alert_key: str
    reason: str


class TelegramAlertDeduplicator:
    """
    Русский комментарий:
    Подавляет повторяющиеся Telegram-alerts.
    CRITICAL-события не подавляются.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS telegram_alert_state (
            alert_key TEXT PRIMARY KEY,
            last_status TEXT NOT NULL,
            last_sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            send_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def should_send(
        self,
        *,
        alert_key: str,
        status: str,
        cooldown_sec: int,
    ) -> TelegramAlertDedupDecision:
        key = str(alert_key).strip()
        current_status = str(status).strip().upper()

        if current_status in {"CRITICAL", "EXTREME"}:
            return TelegramAlertDedupDecision(
                should_send=True,
                alert_key=key,
                reason="критическое_событие_без_подавления",
            )

        row = self._load(key)

        if row is None:
            return TelegramAlertDedupDecision(
                should_send=True,
                alert_key=key,
                reason="первое_сообщение_по_ключу",
            )

        last_status, last_sent_at = row

        age_sec = (datetime.now(timezone.utc) - last_sent_at).total_seconds()

        if str(last_status).upper() != current_status:
            return TelegramAlertDedupDecision(
                should_send=True,
                alert_key=key,
                reason="изменился_статус_события",
            )

        if age_sec >= float(cooldown_sec):
            return TelegramAlertDedupDecision(
                should_send=True,
                alert_key=key,
                reason="истек_cooldown",
            )

        return TelegramAlertDedupDecision(
            should_send=False,
            alert_key=key,
            reason=f"повтор_подавлен_age={round(age_sec, 1)}_cooldown={cooldown_sec}",
        )

    def mark_sent(self, *, alert_key: str, status: str) -> None:
        sql = """
        INSERT INTO telegram_alert_state (
            alert_key,
            last_status,
            last_sent_at,
            send_count,
            updated_at
        )
        VALUES (%s, %s, now(), 1, now())
        ON CONFLICT (alert_key)
        DO UPDATE SET
            last_status = EXCLUDED.last_status,
            last_sent_at = now(),
            send_count = telegram_alert_state.send_count + 1,
            updated_at = now()
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (alert_key, status))
            conn.commit()

    def _load(self, alert_key: str) -> tuple[str, datetime] | None:
        sql = """
        SELECT last_status, last_sent_at
        FROM telegram_alert_state
        WHERE alert_key = %s
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (alert_key,))
                    row = cur.fetchone()
        except Exception:
            return None

        if row is None:
            return None

        return str(row[0]), row[1]
