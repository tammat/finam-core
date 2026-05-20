from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DuplicateFillDecision:
    allowed: bool
    reason: str


class DuplicateFillProtection:
    """Русский комментарий: запрещает повторную обработку FILLED для одного broker_order_id."""

    def check(self, cur, *, broker_order_id: str) -> DuplicateFillDecision:
        if not broker_order_id:
            return DuplicateFillDecision(False, "empty_broker_order_id")

        cur.execute(
            """
            select count(*)
            from execution_intents
            where broker_order_id = %s
              and intent_state = 'FILLED'
            """,
            (str(broker_order_id),),
        )

        count = int(cur.fetchone()[0] or 0)

        if count > 0:
            return DuplicateFillDecision(False, f"duplicate_filled_order:{broker_order_id}")

        return DuplicateFillDecision(True, "fill_not_seen")
