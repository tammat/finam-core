from __future__ import annotations

import json
from datetime import datetime, timezone

import psycopg2

from marketcore.core.profit_funnel_contract_v2 import ProfitFunnelStageV2
from marketcore.services.profit_funnel_source_registry_v2 import observe_profit_funnel_sources_v2


def main() -> None:
    observations = {row.stage: row for row in observe_profit_funnel_sources_v2()}
    now = datetime.now(timezone.utc)
    transitions = []
    stages = tuple(ProfitFunnelStageV2)
    for from_stage, to_stage in zip(stages, stages[1:]):
        left, right = observations[from_stage], observations[to_stage]
        transitions.append({
            "transition_code": f"{from_stage.value}_TO_{to_stage.value}",
            "from_stage": from_stage.value,
            "to_stage": to_stage.value,
            "canonical_cohort_id": None,
            "source_cohort_from": left.cohort_id if left.cohort_count == 1 else None,
            "source_cohort_to": right.cohort_id if right.cohort_count == 1 else None,
            "from_count": left.count,
            "to_count": right.count,
            "linked_count": 0,
            "lineage_status": "UNVERIFIED",
            "reason_code": "CANONICAL_LINK_NOT_PROVEN",
            "evidence": {"from_source": left.source_identity, "to_source": right.source_identity},
        })

    candidate_oos = transitions[2]
    candidate_oos.update(
        lineage_status="BROKEN",
        reason_code="SOURCE_COHORT_ID_MISMATCH",
        evidence={**candidate_oos["evidence"], "candidate_cohort_count": observations[ProfitFunnelStageV2.CANDIDATE].cohort_count},
    )

    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT f.cohort_id::text,count(*)::bigint,count(s.shadow_trade_id)::bigint
                FROM analytics.forward_edge_observation_v1 f
                LEFT JOIN analytics.forward_edge_shadow_trade_v1 s ON s.observation_id=f.observation_id
                GROUP BY f.cohort_id
            """)
            rows = cursor.fetchall()
            forward_shadow = transitions[4]
            if len(rows) == 1:
                cohort_id, forward_count, linked_count = rows[0]
                shadow_count = observations[ProfitFunnelStageV2.SHADOW].count
                proven = forward_count == linked_count == shadow_count
                forward_shadow.update(
                    canonical_cohort_id=cohort_id if proven else None,
                    source_cohort_from=cohort_id,
                    source_cohort_to=cohort_id,
                    from_count=forward_count,
                    to_count=shadow_count,
                    linked_count=linked_count,
                    lineage_status="PROVEN" if proven else "BROKEN",
                    reason_code="OBSERVATION_ID_FULL_MATCH" if proven else "OBSERVATION_ID_LINK_GAP",
                    evidence={**forward_shadow["evidence"], "join_key": "observation_id"},
                )

            for item in transitions:
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_transition_lineage_v2 (
                        transition_code,from_stage,to_stage,canonical_cohort_id,
                        source_cohort_from,source_cohort_to,from_count,to_count,linked_count,
                        lineage_status,reason_code,evidence,observed_at,refreshed_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,clock_timestamp())
                    ON CONFLICT (transition_code) DO UPDATE SET
                        canonical_cohort_id=EXCLUDED.canonical_cohort_id,
                        source_cohort_from=EXCLUDED.source_cohort_from,
                        source_cohort_to=EXCLUDED.source_cohort_to,
                        from_count=EXCLUDED.from_count,to_count=EXCLUDED.to_count,
                        linked_count=EXCLUDED.linked_count,lineage_status=EXCLUDED.lineage_status,
                        reason_code=EXCLUDED.reason_code,evidence=EXCLUDED.evidence,
                        observed_at=EXCLUDED.observed_at,refreshed_at=EXCLUDED.refreshed_at
                """, (
                    item["transition_code"],item["from_stage"],item["to_stage"],item["canonical_cohort_id"],
                    item["source_cohort_from"],item["source_cohort_to"],item["from_count"],item["to_count"],
                    item["linked_count"],item["lineage_status"],item["reason_code"],json.dumps(item["evidence"]),now,
                ))
    print(f"transitions_total={len(transitions)}")
    print(f"proven={sum(item['lineage_status']=='PROVEN' for item in transitions)}")
    print(f"broken={sum(item['lineage_status']=='BROKEN' for item in transitions)}")
    print(f"unverified={sum(item['lineage_status']=='UNVERIFIED' for item in transitions)}")
    print("VERDICT=MARKETCORE_PROFIT_FUNNEL_TRANSITION_LINEAGE_V2_BUILT")


if __name__ == "__main__":
    main()
