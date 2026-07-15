from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import psycopg2
import psycopg2.extras

from marketcore.action.contract_v2 import ActionIntentV2
from marketcore.action.dispatcher_v2 import RiskDecisionV2, RiskVerdictV2


@dataclass(frozen=True, slots=True)
class RiskPermissionStateV2:
    runtime_allowed: bool
    execution_allowed: bool
    micro_live_allowed: bool
    refreshed_at: datetime
    maximum_age_seconds: int


def evaluate_risk_permission_v2(state: RiskPermissionStateV2, guard_code: str, *, now: datetime) -> RiskDecisionV2:
    if now.tzinfo is None or state.refreshed_at.tzinfo is None:
        return RiskDecisionV2(RiskVerdictV2.DENY, "RISK_CLOCK_INVALID", guard_code)
    age_seconds = (now.astimezone(timezone.utc) - state.refreshed_at.astimezone(timezone.utc)).total_seconds()
    if age_seconds < 0 or age_seconds > state.maximum_age_seconds:
        return RiskDecisionV2(RiskVerdictV2.DENY, "RISK_PERMISSION_STALE", guard_code)
    required_permission = {
        "RISK.RESEARCH_RESOURCE_GUARD": True,
        "RISK.RUNTIME_GUARD": state.runtime_allowed,
        "RISK.EXECUTION_GUARD": state.execution_allowed,
        "RISK.MICRO_LIVE_GUARD": state.micro_live_allowed,
    }.get(guard_code)
    if required_permission is None:
        return RiskDecisionV2(RiskVerdictV2.DENY, "RISK_GUARD_UNKNOWN", guard_code)
    if not required_permission:
        return RiskDecisionV2(RiskVerdictV2.DENY, "RISK_PERMISSION_DENIED", guard_code)
    return RiskDecisionV2(RiskVerdictV2.ALLOW, "RISK_PERMISSION_ALLOWED", guard_code)


class PostgresRiskBoundaryV2:
    def __init__(self, connection_factory: Callable = lambda: psycopg2.connect("postgresql:///finam_core")) -> None:
        self._connection_factory = connection_factory

    def evaluate(self, intent: ActionIntentV2, guard_code: str, *, now: datetime) -> RiskDecisionV2:
        del intent
        with self._connection_factory() as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT (config_json->>'presentation_freshness_seconds')::integer AS maximum_age_seconds
                    FROM analytics.risk_configuration_v1
                    WHERE risk_name='DEFAULT' AND enabled=true
                    LIMIT 1
                    """
                )
                config = cursor.fetchone()
                if not config or not config["maximum_age_seconds"] or int(config["maximum_age_seconds"]) <= 0:
                    return RiskDecisionV2(RiskVerdictV2.DENY, "RISK_CONFIGURATION_UNAVAILABLE", guard_code)
                cursor.execute(
                    """
                    SELECT runtime_allowed,execution_allowed,micro_live_allowed,refreshed_at
                    FROM marketcore_ui.risk_summary_v1
                    WHERE id=1
                    """
                )
                permission = cursor.fetchone()
        if not permission:
            return RiskDecisionV2(RiskVerdictV2.DENY, "RISK_PERMISSION_UNAVAILABLE", guard_code)
        return evaluate_risk_permission_v2(
            RiskPermissionStateV2(
                runtime_allowed=bool(permission["runtime_allowed"]),
                execution_allowed=bool(permission["execution_allowed"]),
                micro_live_allowed=bool(permission["micro_live_allowed"]),
                refreshed_at=permission["refreshed_at"],
                maximum_age_seconds=int(config["maximum_age_seconds"]),
            ),
            guard_code,
            now=now,
        )
