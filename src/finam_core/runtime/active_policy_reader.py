from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActivePolicyDecision:
    decision_id: str
    objective: str
    selected_mode: str
    score: float
    net_pnl: float
    expectancy: float
    winrate: float
    active: bool


class ActivePolicyRuntimeReader:
    """Русский комментарий: читает активное policy decision для runtime/replay."""

    def __init__(self, conn: Any):
        self.conn = conn

    def get_active(self, *, objective: str) -> ActivePolicyDecision | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select
                    decision_id,
                    objective,
                    selected_mode,
                    score,
                    net_pnl,
                    expectancy,
                    winrate,
                    active
                from research_policy_decisions
                where objective = %s
                  and active = true
                order by created_at desc, id desc
                limit 1
                """,
                (objective,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return ActivePolicyDecision(
            decision_id=str(row[0]),
            objective=str(row[1]),
            selected_mode=str(row[2]),
            score=float(row[3]),
            net_pnl=float(row[4]),
            expectancy=float(row[5]),
            winrate=float(row[6]),
            active=bool(row[7]),
        )
