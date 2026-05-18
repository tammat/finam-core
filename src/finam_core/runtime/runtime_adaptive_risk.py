from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeAdaptiveRiskDecision:
    allowed: bool
    risk_multiplier: float
    decision: str
    reason: str
    policy_id: str | None = None


class RuntimeAdaptiveRisk:
    """Русский комментарий: читает research regime policy и возвращает runtime risk multiplier."""

    def __init__(self, conn: Any):
        self.conn = conn

    def decide(
        self,
        *,
        regime: str,
        policy_id: str,
    ) -> RuntimeAdaptiveRiskDecision:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select
                    decision,
                    risk_multiplier,
                    reason,
                    policy_id
                from research_regime_policy
                where policy_id = %s
                  and regime = %s
                order by created_at desc, id desc
                limit 1
                """,
                (policy_id, regime),
            )
            row = cur.fetchone()

        if row is None:
            return RuntimeAdaptiveRiskDecision(
                allowed=True,
                risk_multiplier=1.0,
                decision="НЕТ_ПОЛИТИКИ",
                reason=f"policy_not_found:policy_id={policy_id}:regime={regime}",
                policy_id=policy_id,
            )

        decision = str(row[0])
        multiplier = float(row[1] or 0.0)
        reason = str(row[2] or "")

        if decision == "ЗАПРЕТИТЬ":
            return RuntimeAdaptiveRiskDecision(
                allowed=False,
                risk_multiplier=0.0,
                decision=decision,
                reason=reason,
                policy_id=str(row[3]),
            )

        if decision == "НЕДОСТАТОЧНО_ДАННЫХ":
            return RuntimeAdaptiveRiskDecision(
                allowed=False,
                risk_multiplier=0.0,
                decision=decision,
                reason=reason,
                policy_id=str(row[3]),
            )

        return RuntimeAdaptiveRiskDecision(
            allowed=True,
            risk_multiplier=max(0.0, multiplier),
            decision=decision,
            reason=reason,
            policy_id=str(row[3]),
        )
