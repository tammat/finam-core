from __future__ import annotations

import hashlib
import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FORWARD_PASS_SHADOW_OBSERVER_V2"
POLICY_CODE = "FORWARD_PASS_SHADOW_V2"
LOCK_ID = 841903127
NAMESPACE = uuid.UUID("a061b389-cb83-4e31-ae91-c2faec41c393")


def fingerprint(*parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def shadow_status(source_status: str) -> str:
    return {"SIGNAL_PENDING_ENTRY": "PENDING_ENTRY", "OPEN": "OPEN", "CLOSED": "CLOSED"}.get(source_status, "OBSERVING")


def main() -> int:
    run_id = uuid.uuid4()
    admitted = inserted = updated = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                cursor.execute("""INSERT INTO analytics.forward_pass_shadow_run_v1
                    (run_id,status_code,reason_code,finished_at,source_version)
                    VALUES(%s,'SKIPPED','OBSERVER_ALREADY_RUNNING',clock_timestamp(),%s)""",
                    (str(run_id), SOURCE_VERSION))
                print("VERDICT=FORWARD_PASS_SHADOW_OBSERVER_ALREADY_RUNNING")
                return 0
            cursor.execute("""INSERT INTO analytics.forward_pass_shadow_run_v1
                (run_id,status_code,reason_code,source_version)
                VALUES(%s,'RUNNING','OBSERVER_STARTED',%s)""", (str(run_id), SOURCE_VERSION))
            cursor.execute("""
                SELECT g.*,i.hypothesis_id,i.symbol,i.timeframe,i.frozen_parameter_json
                FROM analytics.forward_edge_regime_promotion_gate_v1 g
                JOIN analytics.forward_edge_incubator_v1 i
                  USING(cohort_id,incubator_candidate_id)
                JOIN analytics.forward_pass_shadow_policy_v1 p ON p.policy_code=%s
                WHERE p.enabled AND g.decision_code=p.source_decision_code
                  AND (NOT p.require_review_eligible OR g.review_eligible)
                ORDER BY g.cohort_id,g.incubator_candidate_id,g.policy_code
            """, (POLICY_CODE,))
            eligible = cursor.fetchall()
            eligible_keys = set()
            for row in eligible:
                key = (str(row["cohort_id"]), str(row["incubator_candidate_id"]), row["policy_code"])
                eligible_keys.add(key)
                candidate_fp = fingerprint(POLICY_CODE, *key)
                candidate_id = uuid.uuid5(NAMESPACE, "candidate:" + candidate_fp)
                evidence = {
                    "decision_code": row["decision_code"], "review_eligible": row["review_eligible"],
                    "closed_observations": row["closed_observations"], "calendar_days": row["calendar_days"],
                    "attribution_coverage": str(row["attribution_coverage"]),
                    "positive_regime_share": str(row["positive_regime_share"]),
                    "variant_net_pnl": str(row["variant_net_pnl"]), "reason_codes": row["reason_codes"],
                    "policy_version": row["policy_version"],
                }
                cursor.execute("""
                    INSERT INTO analytics.forward_pass_shadow_candidate_v1(
                      shadow_candidate_id,cohort_id,incubator_candidate_id,hypothesis_id,policy_code,
                      exit_policy_code,strategy_family,symbol,timeframe,parameter_json,forward_evidence,
                      execution_fingerprint,observation_not_before,candidate_status)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp(),'ACTIVE')
                    ON CONFLICT(cohort_id,incubator_candidate_id,exit_policy_code,policy_code)
                    DO UPDATE SET forward_evidence=EXCLUDED.forward_evidence,candidate_status='ACTIVE',
                                  updated_at=clock_timestamp()
                    RETURNING (xmax=0) AS was_inserted,shadow_candidate_id,observation_not_before
                """, (str(candidate_id),key[0],key[1],str(row["hypothesis_id"]),POLICY_CODE,row["policy_code"],
                      row["strategy_family"],row["symbol"],row["timeframe"],
                      psycopg2.extras.Json(row["frozen_parameter_json"]),psycopg2.extras.Json(evidence),candidate_fp))
                candidate = cursor.fetchone()
                admitted += int(candidate["was_inserted"])
                cursor.execute("""
                    SELECT * FROM analytics.forward_edge_observation_v1
                    WHERE cohort_id=%s AND incubator_candidate_id=%s AND signal_ts>%s
                    ORDER BY signal_ts,observation_id
                """, (key[0], key[1], candidate["observation_not_before"]))
                for observation in cursor.fetchall():
                    obs_fp = fingerprint(candidate_fp, observation["observation_id"])
                    obs_id = uuid.uuid5(NAMESPACE, "observation:" + obs_fp)
                    cursor.execute("SELECT 1 FROM analytics.forward_pass_shadow_observation_v1 WHERE execution_fingerprint=%s", (obs_fp,))
                    exists = cursor.fetchone() is not None
                    cursor.execute("""
                        INSERT INTO analytics.forward_pass_shadow_observation_v1(
                          shadow_observation_id,shadow_candidate_id,source_observation_id,cohort_id,
                          incubator_candidate_id,hypothesis_id,symbol,timeframe,side,signal_ts,entry_ts,
                          exit_ts,entry_price,exit_price,qty,gross_pnl,commission,spread_cost,slippage,
                          net_pnl,shadow_status,execution_fingerprint,source_version)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT(execution_fingerprint) DO UPDATE SET
                          entry_ts=EXCLUDED.entry_ts,exit_ts=EXCLUDED.exit_ts,
                          entry_price=EXCLUDED.entry_price,exit_price=EXCLUDED.exit_price,
                          gross_pnl=EXCLUDED.gross_pnl,commission=EXCLUDED.commission,
                          spread_cost=EXCLUDED.spread_cost,slippage=EXCLUDED.slippage,
                          net_pnl=EXCLUDED.net_pnl,shadow_status=EXCLUDED.shadow_status,
                          shadow_only=TRUE,broker_order_sent=FALSE,runtime_allowed=FALSE,
                          execution_enabled=FALSE,updated_at=clock_timestamp()
                    """, (str(obs_id),str(candidate["shadow_candidate_id"]),str(observation["observation_id"]),
                          key[0],key[1],str(row["hypothesis_id"]),row["symbol"],row["timeframe"],
                          observation["side"],observation["signal_ts"],observation["entry_ts"],
                          observation["exit_ts"],observation["entry_price"],observation["exit_price"],
                          observation["gross_pnl"],observation["commission"],observation["spread_cost"],
                          observation["slippage"],observation["net_pnl"],
                          shadow_status(observation["observation_status"]),obs_fp,SOURCE_VERSION))
                    inserted += int(not exists)
                    updated += int(exists)
            cursor.execute("""
                UPDATE analytics.forward_pass_shadow_candidate_v1 c SET
                  candidate_status='SUSPENDED',updated_at=clock_timestamp()
                WHERE c.policy_code=%s AND c.candidate_status='ACTIVE'
                  AND NOT EXISTS(
                    SELECT 1 FROM analytics.forward_edge_regime_promotion_gate_v1 g
                    WHERE g.cohort_id=c.cohort_id AND g.incubator_candidate_id=c.incubator_candidate_id
                      AND g.policy_code=c.exit_policy_code
                      AND g.decision_code='READY_FOR_PAPER_REVIEW' AND g.review_eligible)
            """, (POLICY_CODE,))
            cursor.execute("SELECT count(*) active FROM analytics.forward_pass_shadow_candidate_v1 WHERE candidate_status='ACTIVE'")
            active = cursor.fetchone()["active"]
            cursor.execute("""SELECT count(*) unsafe FROM analytics.forward_pass_shadow_observation_v1
                               WHERE NOT shadow_only OR broker_order_sent OR runtime_allowed OR execution_enabled""")
            unsafe = cursor.fetchone()["unsafe"]
            cursor.execute("""UPDATE analytics.forward_pass_shadow_run_v1 SET
                status_code='COMPLETE',reason_code=%s,candidates_admitted=%s,candidates_active=%s,
                observations_inserted=%s,observations_updated=%s,unsafe_rows=%s,
                finished_at=clock_timestamp() WHERE run_id=%s""",
                ("FORWARD_PASS_CANDIDATES_OBSERVED" if active else "NO_FORWARD_PASS_CANDIDATES",
                 admitted,active,inserted,updated,unsafe,str(run_id)))
    print(f"run_id={run_id}")
    print(f"candidates_admitted={admitted}")
    print(f"candidates_active={active}")
    print(f"observations_inserted={inserted}")
    print(f"observations_updated={updated}")
    print(f"unsafe_rows={unsafe}")
    print("broker_orders=0")
    print("runtime_allowed=0")
    print("live_allowed=0")
    print("VERDICT=FORWARD_PASS_SHADOW_OBSERVER_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
