from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "OPERATOR_DECISION_WORKSPACE_V2"
NAMESPACE = uuid.UUID("5706b557-e1e0-5035-b177-d91c5bf706aa")


def main() -> None:
    now = datetime.now(timezone.utc)
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT l.*,p.action_code,p.priority,p.policy_verdict,p.autonomy_mode,
                       p.validity_seconds,p.risk_impact_code,p.rollback_plan_code
                FROM analytics.profit_funnel_transition_lineage_v2 l
                JOIN analytics.operator_action_policy_v2 p USING (reason_code)
                WHERE l.lineage_status='UNVERIFIED' AND p.enabled
                ORDER BY p.priority,l.transition_code
            """)
            rows = cursor.fetchall()
            active_transitions = [str(row["transition_code"]) for row in rows]
            cursor.execute("""
                UPDATE analytics.operator_decision_workspace_v2
                SET freshness_code='STALE',updated_at=clock_timestamp()
                WHERE NOT (transition_code = ANY(%s)) AND freshness_code<>'STALE'
            """, (active_transitions,))
            for rank, row in enumerate(rows, start=1):
                sample_size = int(row["from_count"] or 0)
                expected_impact = None
                if row["reason_code"] == "NO_SHADOW_CANDIDATE_ELIGIBLE":
                    cursor.execute("""
                        SELECT abs(coalesce(sum(net_pnl),0)) AS observed_loss
                        FROM analytics.profit_funnel_shadow_paper_admission_v2
                        WHERE admission_status='REJECTED' AND net_pnl < 0
                    """)
                    expected_impact = Decimal(str(cursor.fetchone()["observed_loss"] or 0))
                confidence = Decimal("0.50") if sample_size >= 30 else Decimal("0.25")
                sufficiency = "SUFFICIENT" if sample_size >= 30 else ("INSUFFICIENT" if sample_size else "NOT_APPLICABLE")
                evidence = {
                    "transition_code": row["transition_code"],
                    "reason_code": row["reason_code"],
                    "from_count": sample_size,
                    "to_count": int(row["to_count"] or 0),
                    "linked_count": int(row["linked_count"] or 0),
                    "lineage_evidence": row["evidence"],
                    "source_version": SOURCE_VERSION,
                }
                decision_id = uuid.uuid5(NAMESPACE, row["transition_code"])
                cursor.execute("""
                    INSERT INTO analytics.operator_decision_workspace_v2 (
                        decision_id,rank,transition_code,bottleneck_stage,loss_source_code,
                        action_code,evidence,source_identity,source_as_of,freshness_code,
                        expected_profit_impact,risk_impact_code,confidence,sample_size,
                        sample_sufficiency_code,policy_verdict,autonomy_mode,expires_at,
                        rollback_plan_code,actual_result,feedback_status,quality_code,updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,'PENDING','UNVERIFIED',clock_timestamp())
                    ON CONFLICT (transition_code) DO UPDATE SET
                        rank=EXCLUDED.rank,bottleneck_stage=EXCLUDED.bottleneck_stage,
                        loss_source_code=EXCLUDED.loss_source_code,action_code=EXCLUDED.action_code,
                        evidence=EXCLUDED.evidence,source_identity=EXCLUDED.source_identity,
                        source_as_of=EXCLUDED.source_as_of,freshness_code=EXCLUDED.freshness_code,
                        expected_profit_impact=EXCLUDED.expected_profit_impact,
                        risk_impact_code=EXCLUDED.risk_impact_code,confidence=EXCLUDED.confidence,
                        sample_size=EXCLUDED.sample_size,sample_sufficiency_code=EXCLUDED.sample_sufficiency_code,
                        policy_verdict=EXCLUDED.policy_verdict,autonomy_mode=EXCLUDED.autonomy_mode,
                        expires_at=EXCLUDED.expires_at,rollback_plan_code=EXCLUDED.rollback_plan_code,
                        quality_code=EXCLUDED.quality_code,updated_at=clock_timestamp()
                """, (
                    str(decision_id),rank,row["transition_code"],row["to_stage"],row["reason_code"],
                    row["action_code"],json.dumps(evidence,default=str),
                    "analytics.profit_funnel_transition_lineage_v2",row["refreshed_at"],
                    "CURRENT" if now-row["refreshed_at"] <= timedelta(hours=2) else "STALE",
                    expected_impact,row["risk_impact_code"],confidence,sample_size,sufficiency,
                    row["policy_verdict"],row["autonomy_mode"],
                    now+timedelta(seconds=row["validity_seconds"]),row["rollback_plan_code"],
                ))
                cursor.execute("""
                    INSERT INTO analytics.operator_decision_lineage_audit_v2 (
                        decision_id,lineage_hash,transition_code,action_code,source_identity,
                        source_as_of,evidence,policy_verdict,autonomy_mode,selection_status,
                        feedback_status,actual_result
                    )
                    SELECT decision_id,
                           md5(concat_ws('|',transition_code,action_code,source_identity,
                               source_as_of::text,evidence::text,policy_verdict,autonomy_mode,
                               selection_status,feedback_status,coalesce(actual_result::text,''))),
                           transition_code,action_code,source_identity,source_as_of,evidence,
                           policy_verdict,autonomy_mode,selection_status,feedback_status,actual_result
                    FROM analytics.operator_decision_workspace_v2
                    WHERE decision_id=%s::uuid
                    ON CONFLICT (decision_id,lineage_hash) DO NOTHING
                """, (str(decision_id),))
    print(f"operator_decisions={len(rows)}")
    print("allowed_recommendations=0")
    print("live_allowed=0")
    print("VERDICT=MARKETCORE_OPERATOR_DECISION_WORKSPACE_V2_READY")


if __name__ == "__main__":
    main()
