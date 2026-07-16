from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras


SOURCE_VERSION = "OOS_FORWARD_CLEAN_COHORT_ADMISSION_V1"
POLICY_VERSION = "OOS_FORWARD_ADMISSION_POLICY_V1"
NAMESPACE = uuid.UUID("6f24d196-3222-5ef6-81b2-111810e08ed0")


def family(strategy_code: str) -> str:
    code = strategy_code.upper()
    if any(marker in code for marker in ("MEAN", "RSI", "BOLLINGER", "VWAP")):
        return "MEAN_REVERSION"
    if any(marker in code for marker in ("MOMENTUM", "IMPULSE")):
        return "MOMENTUM"
    return "BREAKOUT"


def canonical_execution(row: dict) -> tuple[str, dict]:
    specification = {
        "family": family(row["strategy_code"]),
        "symbol": row["symbol"],
        "timeframe": row["timeframe"],
        "parameters": row["parameter_json"] or {},
        "runner": "FORWARD_EDGE_OBSERVATION_WORKER_V1",
    }
    canonical = json.dumps(specification, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest(), specification


def main() -> None:
    now = datetime.now(timezone.utc)
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT h.*,c.strategy_code,c.symbol,c.timeframe,c.parameter_hash,c.parameter_json,
                       o.oos_trades,o.oos_profit_factor,o.oos_expectancy,o.folds_passed,o.folds_total
                FROM analytics.profit_funnel_oos_forward_handoff_v2 h
                JOIN analytics.edge_candidate_v1 c USING(candidate_uuid)
                JOIN analytics.edge_oos_result_v1 o ON o.id=h.oos_result_id
                WHERE h.handoff_status='PENDING'
                  AND o.verdict_code='OOS_PASS' AND o.promotion_allowed=true
                ORDER BY c.candidate_uuid
                FOR UPDATE OF h
            """)
            rows = [dict(row) for row in cursor.fetchall()]
            if not rows:
                print("pending_handoffs=0")
                print("VERDICT=OOS_FORWARD_CLEAN_COHORT_ALREADY_DECIDED")
                return

            enriched = []
            for row in rows:
                fingerprint, specification = canonical_execution(row)
                enriched.append((row, fingerprint, specification))

            representatives = {}
            for row, fingerprint, specification in enriched:
                current = representatives.get(fingerprint)
                rank = (float(row["oos_profit_factor"]), str(row["candidate_uuid"]))
                if current is None or rank > current[0]:
                    representatives[fingerprint] = (rank, row, specification)

            cohort_seed = "|".join(sorted(representatives))
            cohort_id = uuid.uuid5(NAMESPACE, "cohort:" + cohort_seed)
            cursor.execute("""
                UPDATE analytics.forward_edge_baseline_v1
                SET cohort_id=%s,frozen_at=%s,
                    frozen_reason='Clean cohort admitted from canonical OOS PASS handoffs',
                    source_version=%s
                WHERE baseline_key='EDGE_SEARCH'
            """, (str(cohort_id), now, SOURCE_VERSION))

            admitted = rejected = 0
            for row, fingerprint, specification in enriched:
                representative = representatives[fingerprint][1]
                passed = row["candidate_uuid"] == representative["candidate_uuid"]
                decision_code = "PASS" if passed else "FAIL"
                reason_code = "FORWARD_COHORT_ADMISSION_PASS" if passed else "DUPLICATE_EXECUTION_FINGERPRINT"
                decision_id = uuid.uuid5(NAMESPACE, "decision:" + str(row["handoff_id"]))
                evidence = {
                    "strategy_code": row["strategy_code"], "symbol": row["symbol"],
                    "timeframe": row["timeframe"], "parameter_json": row["parameter_json"] or {},
                    "oos_trades": row["oos_trades"], "oos_profit_factor": float(row["oos_profit_factor"]),
                    "oos_expectancy": float(row["oos_expectancy"]),
                    "folds_passed": row["folds_passed"], "folds_total": row["folds_total"],
                    "representative_candidate_uuid": str(representative["candidate_uuid"]),
                }
                cursor.execute("""
                    INSERT INTO analytics.profit_funnel_oos_forward_admission_decision_v1 (
                        decision_id,handoff_id,candidate_uuid,decision_code,reason_code,
                        execution_fingerprint,target_cohort_id,evidence,policy_version,evaluator_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    str(decision_id),str(row["handoff_id"]),str(row["candidate_uuid"]),decision_code,
                    reason_code,fingerprint,str(cohort_id) if passed else None,
                    psycopg2.extras.Json(evidence),POLICY_VERSION,SOURCE_VERSION,
                ))
                cursor.execute("""
                    UPDATE analytics.profit_funnel_oos_forward_handoff_v2
                    SET handoff_status=%s,reason_code=%s,target_cohort_id=%s,
                        source_version=%s,updated_at=clock_timestamp()
                    WHERE handoff_id=%s
                """, (
                    "ADMITTED" if passed else "REJECTED",reason_code,
                    str(cohort_id) if passed else None,SOURCE_VERSION,str(row["handoff_id"]),
                ))
                if not passed:
                    rejected += 1
                    continue

                hypothesis_id = uuid.uuid5(NAMESPACE, "hypothesis:" + fingerprint)
                cursor.execute("""
                    INSERT INTO analytics.canonical_hypothesis_registry_v1 (
                        hypothesis_id,hypothesis_fingerprint,candidate_hash,strategy_family,
                        engine_code,parameter_json,lifecycle_state,source_version
                    ) VALUES (%s,%s,%s,%s,'FORWARD_EDGE_OBSERVATION_WORKER_V1',%s,'FORWARD',%s)
                    ON CONFLICT (hypothesis_fingerprint) DO UPDATE SET
                        lifecycle_state='FORWARD',updated_at=clock_timestamp()
                    RETURNING hypothesis_id
                """, (
                    str(hypothesis_id),fingerprint,row["parameter_hash"],specification["family"],
                    psycopg2.extras.Json(row["parameter_json"] or {}),SOURCE_VERSION,
                ))
                hypothesis_id = cursor.fetchone()["hypothesis_id"]
                cursor.execute("""
                    INSERT INTO analytics.forward_edge_incubator_v1 (
                        cohort_id,incubator_candidate_id,hypothesis_id,source_trial_id,source_kind,
                        strategy_family,symbol,timeframe,frozen_parameter_json,frozen_fingerprint,
                        source_gross_pf,activated_at,observation_not_before,minimum_observations,
                        minimum_calendar_days,incubator_status,trust_state,paper_state,
                        promotion_allowed,live_allowed,source_version
                    ) VALUES (%s,%s,%s,NULL,'OOS_PASS_CLEAN_HANDOFF',%s,%s,%s,%s,%s,%s,%s,%s,
                              30,30,'ACCUMULATING','PENDING','NOT_ELIGIBLE',false,false,%s)
                    ON CONFLICT (cohort_id,incubator_candidate_id) DO NOTHING
                """, (
                    str(cohort_id),str(row["forward_candidate_id"]),str(hypothesis_id),
                    specification["family"],row["symbol"],row["timeframe"],
                    psycopg2.extras.Json(row["parameter_json"] or {}),fingerprint,
                    row["oos_profit_factor"],now,now,SOURCE_VERSION,
                ))
                admitted += 1

    print(f"target_cohort_id={cohort_id}")
    print(f"pending_handoffs={len(rows)}")
    print(f"admitted_unique_executions={admitted}")
    print(f"rejected_duplicate_executions={rejected}")
    print("historical_observations_imported=0")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=OOS_FORWARD_CLEAN_COHORT_ADMITTED")


if __name__ == "__main__":
    main()
