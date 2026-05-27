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
    """Русский комментарий: advisory-слой сессионного edge без блокировки сделок."""

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
        normalized = str(advisory_status or "").strip().lower()

        if normalized in {"подтверждено", "confirmed", "благоприятно"}:
            return SessionEdgeDecision(
                mode=self.mode,
                status="confirmed",
                reason="СЕССИОННЫЙ_EDGE_ПОДТВЕРЖДЕН",
                session_bucket=session_bucket,
                hour_utc=hour_utc,
            )

        if normalized in {"несоответствие", "mismatch", "неблагоприятно"}:
            return SessionEdgeDecision(
                mode=self.mode,
                status="mismatch",
                reason="СЕССИОННЫЙ_EDGE_НЕСООТВЕТСТВИЕ",
                session_bucket=session_bucket,
                hour_utc=hour_utc,
            )

        if normalized in {"недостаточно_данных", "insufficient_data"}:
            return SessionEdgeDecision(
                mode=self.mode,
                status="insufficient_data",
                reason="СЕССИОННЫЙ_EDGE_НЕДОСТАТОЧНО_ДАННЫХ",
                session_bucket=session_bucket,
                hour_utc=hour_utc,
            )

        return SessionEdgeDecision(
            mode=self.mode,
            status="neutral",
            reason=advisory_reason or "СЕССИОННЫЙ_EDGE_НЕЙТРАЛЬНО",
            session_bucket=session_bucket,
            hour_utc=hour_utc,
        )
