from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_REMEDIATION_V1"


def main() -> int:
    created = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT r.*,coalesce(max(o.exit_ts),clock_timestamp()) cutoff
                FROM analytics.forward_pass_readiness_v1 r
                LEFT JOIN analytics.forward_edge_observation_v1 o USING(cohort_id,incubator_candidate_id)
                WHERE r.decision_code='HOLD_RESEARCH'
                GROUP BY r.cohort_id,r.incubator_candidate_id,r.policy_code,r.closed_observations,r.calendar_days,
                         r.attribution_coverage,r.tested_regimes,r.positive_regime_share,r.variant_net_pnl,
                         r.evidence_progress_pct,r.regime_progress_pct,r.overall_progress_pct,r.readiness_rank,
                         r.decision_code,r.reason_codes,r.source_updated_at,r.refreshed_at
                ORDER BY r.readiness_rank LIMIT 5""")
            candidates = cur.fetchall()
            if not candidates:
                raise RuntimeError("FORWARD_REMEDIATION_NO_READINESS_DATA")
            for row in candidates:
                reasons = list(row["reason_codes"] or [])
                if "INSUFFICIENT_CLOSED_OBSERVATIONS" in reasons or "INSUFFICIENT_CALENDAR_DAYS" in reasons:
                    code = "ACCUMULATE_FORWARD_EVIDENCE"
                elif any(reason in reasons for reason in ("INSUFFICIENT_REGIME_COVERAGE","INSUFFICIENT_TESTED_REGIMES","LOW_POSITIVE_REGIME_SHARE")):
                    code = "EXPAND_REGIME_OBSERVATION"
                else:
                    code = "FUTURE_ONLY_RESEARCH_REFINEMENT"
                scenario_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{row['cohort_id']}:{row['incubator_candidate_id']}:{row['policy_code']}:{code}:{SOURCE_VERSION}")
                policy = {"parameter_mutation_allowed": False, "selection_uses_final_holdout": False,
                          "promotion_requires_pass": True, "automatic_execution": False}
                cur.execute("""INSERT INTO analytics.forward_remediation_scenario_v1
                    (scenario_id,cohort_id,incubator_candidate_id,policy_code,scenario_code,reason_codes,action_policy,
                     selection_cutoff_ts,observation_not_before,selection_uses_final_holdout,status_code,source_version)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,false,'WAITING_FUTURE_DATA',%s)
                    ON CONFLICT(cohort_id,incubator_candidate_id,policy_code,scenario_code,source_version)
                    DO UPDATE SET reason_codes=EXCLUDED.reason_codes,action_policy=EXCLUDED.action_policy,
                    selection_cutoff_ts=EXCLUDED.selection_cutoff_ts,observation_not_before=EXCLUDED.observation_not_before,
                    updated_at=clock_timestamp()""",
                    (str(scenario_id),row["cohort_id"],row["incubator_candidate_id"],row["policy_code"],code,
                     json.dumps(reasons),json.dumps(policy),row["cutoff"],row["cutoff"],SOURCE_VERSION))
                created += 1
            cur.execute("""UPDATE analytics.forward_pass_stage_status_v1 SET status_code=%s,progress_pct=%s,
                item_count=%s,reason_code=%s,evidence=%s,updated_at=clock_timestamp() WHERE step_order=5""",
                ("COMPLETE" if created else "WAITING",100 if created else 0,created,
                 "FUTURE_ONLY_SCENARIOS_STORED" if created else "AWAITING_SCENARIOS",
                 json.dumps({"selection_uses_final_holdout":False,"scenarios":created})))
    print(f"scenarios={created}")
    print("VERDICT=FORWARD_REMEDIATION_SCENARIOS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
