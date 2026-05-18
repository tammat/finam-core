from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from finam_core.research.regime_risk_policy import RegimePolicyDecision


class RegimePolicyRepository:
    """Русский комментарий: сохраняет risk-policy по режимам в PostgreSQL."""

    def __init__(self, conn: Any):
        self.conn = conn

    def save_policy(
        self,
        *,
        policy_id: str,
        campaign_pattern: str,
        decisions: list[RegimePolicyDecision],
    ) -> int:
        saved = 0

        with self.conn.cursor() as cur:
            for d in decisions:
                payload = asdict(d)

                cur.execute(
                    """
                    INSERT INTO research_regime_policy (
                        policy_id,
                        campaign_pattern,
                        regime,
                        trend,
                        volatility,
                        decision,
                        risk_multiplier,
                        reason,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    """,
                    (
                        policy_id,
                        campaign_pattern,
                        d.regime,
                        d.trend,
                        d.volatility,
                        d.decision,
                        d.risk_multiplier,
                        d.reason,
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )
                saved += cur.rowcount

        self.conn.commit()
        return saved
