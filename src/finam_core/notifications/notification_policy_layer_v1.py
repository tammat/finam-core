from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NotificationPolicyDecisionV1:
    allowed: bool
    reason: str
    severity: str
    category: str
    quiet_hours_active: bool
    aggregate_only: bool


class NotificationPolicyLayerV1:
    """
    Русский комментарий:
    Policy layer для notification stack.

    Задачи:
    - quiet hours
    - severity policy
    - aggregate-only policy
    - suppression policy

    Ничего не отправляет.
    Только принимает policy decision.
    """

    DEFAULT_ALWAYS_SEND = {
        "CRITICAL",
    }

    DEFAULT_AGGREGATE_ONLY = {
        "INFO",
        "NORMAL",
    }

    def __init__(
        self,
        *,
        quiet_hours_enabled: bool = True,
        quiet_hours_start: int = 23,
        quiet_hours_end: int = 7,
    ) -> None:
        self.quiet_hours_enabled = quiet_hours_enabled
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end

    def evaluate(
        self,
        *,
        severity: str,
        category: str,
        now_utc: datetime | None = None,
    ) -> NotificationPolicyDecisionV1:

        severity = str(severity or "NORMAL").upper()
        category = str(category or "UNKNOWN")

        now_utc = now_utc or datetime.now(timezone.utc)

        quiet_hours_active = self._quiet_hours_active(now_utc)

        if severity in self.DEFAULT_ALWAYS_SEND:
            return NotificationPolicyDecisionV1(
                allowed=True,
                reason="critical_always_allowed",
                severity=severity,
                category=category,
                quiet_hours_active=quiet_hours_active,
                aggregate_only=False,
            )

        if severity == "WARNING":
            if quiet_hours_active:
                return NotificationPolicyDecisionV1(
                    allowed=False,
                    reason="quiet_hours_warning_suppressed",
                    severity=severity,
                    category=category,
                    quiet_hours_active=True,
                    aggregate_only=False,
                )

            return NotificationPolicyDecisionV1(
                allowed=True,
                reason="warning_allowed",
                severity=severity,
                category=category,
                quiet_hours_active=False,
                aggregate_only=False,
            )

        if severity in self.DEFAULT_AGGREGATE_ONLY:
            return NotificationPolicyDecisionV1(
                allowed=False,
                reason="aggregate_only",
                severity=severity,
                category=category,
                quiet_hours_active=quiet_hours_active,
                aggregate_only=True,
            )

        return NotificationPolicyDecisionV1(
            allowed=False,
            reason="unknown_policy",
            severity=severity,
            category=category,
            quiet_hours_active=quiet_hours_active,
            aggregate_only=False,
        )

    def _quiet_hours_active(self, now_utc: datetime) -> bool:
        if not self.quiet_hours_enabled:
            return False

        hour = int(now_utc.hour)

        if self.quiet_hours_start > self.quiet_hours_end:
            return (
                hour >= self.quiet_hours_start
                or hour < self.quiet_hours_end
            )

        return (
            self.quiet_hours_start
            <= hour
            < self.quiet_hours_end
        )
