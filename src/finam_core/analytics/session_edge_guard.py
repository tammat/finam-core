from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionEdgeDecision:
    mode: str
    status: str
    reason: str
    session_bucket: str
    hour_utc: int


class SessionEdgeGuard:
    """Русский комментарий: analytics-only advisory layer."""

    def __init__(self, mode: str = "soft_advisory"):
        self.mode = mode

    def decide(
        self,
        *,
        session_bucket: str,
        hour_utc: int,
        advisory_status: str,
        advisory_reason: str,
    ) -> SessionEdgeDecision:

        normalized = str(advisory_status or "").lower()

        if normalized == "confirmed":
            return SessionEdgeDecision(
                mode=self.mode,
                status="confirmed",
                reason="SESSION_EDGE_CONFIRMED",
                session_bucket=session_bucket,
                hour_utc=hour_utc,
            )

        if normalized == "mismatch":
            return SessionEdgeDecision(
                mode=self.mode,
                status="mismatch",
                reason="SESSION_EDGE_MISMATCH",
                session_bucket=session_bucket,
                hour_utc=hour_utc,
            )

        if normalized == "insufficient_data":
            return SessionEdgeDecision(
                mode=self.mode,
                status="insufficient_data",
                reason="SESSION_EDGE_INSUFFICIENT_DATA",
                session_bucket=session_bucket,
                hour_utc=hour_utc,
            )

        return SessionEdgeDecision(
            mode=self.mode,
            status="neutral",
            reason=advisory_reason or "SESSION_EDGE_NEUTRAL",
            session_bucket=session_bucket,
            hour_utc=hour_utc,
        )
