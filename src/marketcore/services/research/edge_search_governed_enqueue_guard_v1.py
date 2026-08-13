from __future__ import annotations

from dataclasses import dataclass

from psycopg2.extras import RealDictCursor


ACTIVE_STATUSES = ("PENDING", "RUNNING")


@dataclass(frozen=True)
class GovernedEnqueueDecisionV1:
    target_id: str
    decision: str
    reason: str
    active_requests: int
    active_request_id: str | None


def evaluate_governed_enqueue_v1(
    conn,
    *,
    target_id: str,
) -> GovernedEnqueueDecisionV1:
    target = target_id.strip()

    if not target.startswith("TARGETED_V1|"):
        return GovernedEnqueueDecisionV1(
            target_id=target,
            decision="REJECT",
            reason="INVALID_TARGETED_V1_ID",
            active_requests=0,
            active_request_id=None,
        )

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                request_id,
                status,
                requested_at
            FROM marketcore_action.command_request_v2
            WHERE target_id=%s
              AND status = ANY(%s)
            ORDER BY requested_at DESC
            """,
            (
                target,
                list(ACTIVE_STATUSES),
            ),
        )

        rows = list(cur.fetchall())

    if len(rows) > 1:
        return GovernedEnqueueDecisionV1(
            target_id=target,
            decision="REJECT",
            reason="MULTIPLE_ACTIVE_REQUESTS",
            active_requests=len(rows),
            active_request_id=str(rows[0]["request_id"]),
        )

    if len(rows) == 1:
        return GovernedEnqueueDecisionV1(
            target_id=target,
            decision="SKIP",
            reason="ALREADY_ACTIVE",
            active_requests=1,
            active_request_id=str(rows[0]["request_id"]),
        )

    return GovernedEnqueueDecisionV1(
        target_id=target,
        decision="ADMIT_SHADOW",
        reason="NO_ACTIVE_REQUEST",
        active_requests=0,
        active_request_id=None,
    )
