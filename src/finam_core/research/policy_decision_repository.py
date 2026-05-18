from __future__ import annotations

import json
from typing import Any


class PolicyDecisionRepository:
    """Русский комментарий: сохраняет выбранную policy decision в PostgreSQL."""

    def __init__(self, conn: Any):
        self.conn = conn

    def save_decision(self, *, decision: dict, active: bool = False) -> int:
        with self.conn.cursor() as cur:
            if active:
                cur.execute(
                    """
                    update research_policy_decisions
                    set active = false
                    where objective = %s and active = true
                    """,
                    (decision["objective"],),
                )

            cur.execute(
                """
                insert into research_policy_decisions (
                    decision_id,
                    report_id,
                    objective,
                    selected_mode,
                    score,
                    net_pnl,
                    expectancy,
                    winrate,
                    active,
                    raw_json
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                """,
                (
                    decision["decision_id"],
                    decision["report_id"],
                    decision["objective"],
                    decision["mode"],
                    decision["score"],
                    decision["net_pnl"],
                    decision["expectancy"],
                    decision["winrate"],
                    active,
                    json.dumps(decision, ensure_ascii=False, default=str),
                ),
            )

        self.conn.commit()
        return 1
