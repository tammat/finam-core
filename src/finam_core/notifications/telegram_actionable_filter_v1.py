from __future__ import annotations

import os


class TelegramActionableFilterV1:
    """
    Русский комментарий:
    Центральный фильтр Telegram-уведомлений.

    Цель:
    - оставить только сообщения по активным ручным сделкам;
    - оставить только реальные точки входа;
    - не слать телеметрию, debug, healthcheck, governance population/effectiveness.
    """

    ALLOW_MARKERS = (
        "REAL_ENTRY_SIGNAL",
        "MANUAL_POSITION_ALERT",
        "MANUAL_POSITION",
        "PROTECTIVE_STOP_ALERT",
        "TAKE_PROFIT_ALERT",
        "STOP_LOSS_ALERT",
        "RISK_CRITICAL",
        "Точка входа",
        "точка входа",
        "Реальная точка входа",
        "Активная ручная сделка",
        "ручная позиция",
        "ручная сделка",
        "Стоп-лосс достигнут",
        "Тейк-профит достигнут",
        "Защитный стоп",
        "стоп",
        "тейк",
    )

    BLOCK_MARKERS = (
        "RUNTIME_GOVERNANCE_POPULATION",
        "RUNTIME_GOVERNANCE_EFFECTIVENESS",
        "RUNTIME_GOVERNANCE_FORCED",
        "forced_runtime_governance_observation",
        "FORCED_OBSERVATION",
        "POPULATION_STATUS",
        "HEALTHCHECK",
        "RUNTIME_HEALTH",
        "REGIME",
        "PIPE_VOL_GATE_OK",
        "PIPE_SESSION_BLOCK",
        "WATCHLIST",
        "DIGEST",
        "GRAFANA",
        "CALENDAR",
        "DRIFT",
        "ANOMALY",
        "MTM",
        "PORTFOLIO_MTM",
        "ADVISORY_ONLY",
        "RUNTIME_CONTROL",
        "DEBUG",
    )

    def enabled(self) -> bool:
        return os.getenv("TELEGRAM_ACTIONABLE_ONLY", "1") == "1"

    def allows(self, text: str) -> bool:
        if not self.enabled():
            return True

        normalized = str(text or "")

        if not normalized.strip():
            return False

        for marker in self.BLOCK_MARKERS:
            if marker in normalized:
                return False

        for marker in self.ALLOW_MARKERS:
            if marker in normalized:
                return True

        return False

    def reason(self, text: str) -> str:
        if not self.enabled():
            return "filter_disabled"

        normalized = str(text or "")

        if not normalized.strip():
            return "empty_text"

        for marker in self.BLOCK_MARKERS:
            if marker in normalized:
                return f"blocked_marker:{marker}"

        for marker in self.ALLOW_MARKERS:
            if marker in normalized:
                return f"allowed_marker:{marker}"

        return "not_actionable"
