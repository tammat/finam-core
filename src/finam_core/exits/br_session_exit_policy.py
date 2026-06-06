from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BrSessionExitDecision:
    should_exit: bool
    reason: str
    policy: str


class BrSessionExitPolicy:
    """
    Research-only политика выхода для Brent.

    Правило:
    закрывать позицию в конце торговой сессии.
    Runtime/paper pipeline не изменяет.
    """

    POLICY_NAME = "BR_SESSION_EXIT_V1_1"

    def __init__(self, session_close_hour: int = 23, session_close_minute: int = 45):
        self.session_close_hour = session_close_hour
        self.session_close_minute = session_close_minute

    def evaluate(
        self,
        *,
        symbol: str,
        position_open: bool,
        current_ts: datetime,
    ) -> BrSessionExitDecision:
        if not position_open:
            return BrSessionExitDecision(False, "no_position", self.POLICY_NAME)

        if not str(symbol or "").startswith("BR"):
            return BrSessionExitDecision(False, "not_br_symbol", self.POLICY_NAME)

        if current_ts.hour > self.session_close_hour:
            return BrSessionExitDecision(True, "session_close", self.POLICY_NAME)

        if (
            current_ts.hour == self.session_close_hour
            and current_ts.minute >= self.session_close_minute
        ):
            return BrSessionExitDecision(True, "session_close", self.POLICY_NAME)

        return BrSessionExitDecision(False, "hold", self.POLICY_NAME)
