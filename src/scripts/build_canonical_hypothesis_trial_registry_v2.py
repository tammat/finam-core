from __future__ import annotations

import hashlib
import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "CANONICAL_HYPOTHESIS_TRIAL_REGISTRY_V2"
HYPOTHESIS_NAMESPACE = uuid.UUID("f18ccb22-fd87-58b2-a6e3-85e58a1769f4")
TRIAL_NAMESPACE = uuid.UUID("0974904e-71bc-58fd-b5a0-e2a18e88bb48")


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.canonical_hypothesis_registry_v1 (
                    hypothesis_id uuid PRIMARY KEY,
                    hypothesis_fingerprint text NOT NULL UNIQUE,
                    candidate_hash text NOT NULL,
                    strategy_family text NOT NULL,
                    engine_code text NOT NULL,
                    parameter_json jsonb NOT NULL,
                    lifecycle_state text NOT NULL,
                    source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                );
                CREATE INDEX IF NOT EXISTS canonical_hypothesis_candidate_idx
                    ON analytics.canonical_hypothesis_registry_v1(candidate_hash);
                CREATE TABLE IF NOT EXISTS analytics.hypothesis_trial_registry_v2 (
                    trial_id uuid PRIMARY KEY,
                    hypothesis_id uuid NOT NULL REFERENCES analytics.canonical_hypothesis_registry_v1(hypothesis_id),
                    execution_run_id uuid,
                    candidate_hash text NOT NULL,
                    engine_code text NOT NULL,
                    symbol text,
                    timeframe text,
                    data_version text NOT NULL,
                    validation_trades integer NOT NULL DEFAULT 0,
                    oos_trades integer NOT NULL DEFAULT 0,
                    oos_profit_factor numeric NOT NULL DEFAULT 0,
                    oos_expectancy numeric NOT NULL DEFAULT 0,
                    folds_passed integer NOT NULL DEFAULT 0,
                    adjusted_p_value numeric NOT NULL DEFAULT 1,
                    trial_state text NOT NULL,
                    verdict_code text NOT NULL,
                    reason_code text NOT NULL,
                    trust_state text NOT NULL DEFAULT 'PENDING',
                    paper_state text NOT NULL DEFAULT 'NOT_ELIGIBLE',
                    promotion_allowed boolean NOT NULL DEFAULT false,
                    source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now(),
                    UNIQUE(execution_run_id,candidate_hash)
                );
                CREATE INDEX IF NOT EXISTS hypothesis_trial_hypothesis_idx
                    ON analytics.hypothesis_trial_registry_v2(hypothesis_id,created_at DESC);
            """)
            cur.execute("""SELECT parameter_space_run_id FROM analytics.hypothesis_parameter_space_v2
                ORDER BY created_at DESC LIMIT 1""")
            parameter_run = cur.fetchone()
            if not parameter_run:
                raise RuntimeError("NO_PARAMETER_SPACE_V2")
            cur.execute("""SELECT execution_run_id FROM analytics.strategy_hypothesis_execution_run_v2
                WHERE parameter_space_run_id=%s ORDER BY created_at DESC LIMIT 1""",
                (parameter_run["parameter_space_run_id"],))
            execution_run = cur.fetchone()
            execution_run_id = execution_run["execution_run_id"] if execution_run else None
            cur.execute("""SELECT candidate_hash,strategy_family,engine_code,parameter_json
                FROM analytics.hypothesis_parameter_space_v2 WHERE parameter_space_run_id=%s AND enabled=true
                ORDER BY candidate_hash""", (parameter_run["parameter_space_run_id"],))
            candidates = cur.fetchall()
            linked_results = 0

            for candidate in candidates:
                identity = {
                    "strategy_family": candidate["strategy_family"],
                    "engine_code": candidate["engine_code"],
                    "parameters": candidate["parameter_json"],
                }
                identity_json = canonical_json(identity)
                fingerprint = hashlib.sha256(identity_json.encode("utf-8")).hexdigest()
                hypothesis_id = uuid.uuid5(HYPOTHESIS_NAMESPACE, fingerprint)
                cur.execute("""INSERT INTO analytics.canonical_hypothesis_registry_v1
                    (hypothesis_id,hypothesis_fingerprint,candidate_hash,strategy_family,engine_code,
                     parameter_json,lifecycle_state,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,'GENERATED',%s)
                    ON CONFLICT(hypothesis_id) DO UPDATE SET candidate_hash=excluded.candidate_hash,
                      lifecycle_state=excluded.lifecycle_state,source_version=excluded.source_version,updated_at=now()""",
                    (str(hypothesis_id),fingerprint,candidate["candidate_hash"],candidate["strategy_family"],
                     candidate["engine_code"],psycopg2.extras.Json(candidate["parameter_json"]),SOURCE_VERSION))

                if not execution_run_id:
                    continue
                cur.execute("""SELECT symbol,timeframe,validation_trades,oos_trades,oos_profit_factor,
                           oos_expectancy,folds_passed,adjusted_p_value,verdict_code,reason_code
                    FROM analytics.strategy_hypothesis_execution_result_v2
                    WHERE execution_run_id=%s AND candidate_hash=%s""",
                    (execution_run_id,candidate["candidate_hash"]))
                result = cur.fetchone()
                if not result:
                    continue
                linked_results += 1
                trial_id = uuid.uuid5(TRIAL_NAMESPACE, f"{execution_run_id}:{hypothesis_id}:{result['symbol']}:{result['timeframe']}")
                trial_state = "COMPLETE" if result["verdict_code"] in {"OOS_PASS", "OOS_FAIL"} else "UNVERIFIED"
                trust_state = "PENDING" if result["verdict_code"] == "OOS_PASS" else "NOT_ELIGIBLE"
                cur.execute("""INSERT INTO analytics.hypothesis_trial_registry_v2
                    (trial_id,hypothesis_id,execution_run_id,candidate_hash,engine_code,symbol,timeframe,data_version,
                     validation_trades,oos_trades,oos_profit_factor,oos_expectancy,folds_passed,adjusted_p_value,
                     trial_state,verdict_code,reason_code,trust_state,paper_state,promotion_allowed,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'NOT_ELIGIBLE',false,%s)
                    ON CONFLICT(execution_run_id,candidate_hash) DO UPDATE SET
                      hypothesis_id=excluded.hypothesis_id,trial_state=excluded.trial_state,
                      symbol=excluded.symbol,timeframe=excluded.timeframe,
                      validation_trades=excluded.validation_trades,oos_trades=excluded.oos_trades,
                      oos_profit_factor=excluded.oos_profit_factor,oos_expectancy=excluded.oos_expectancy,
                      folds_passed=excluded.folds_passed,adjusted_p_value=excluded.adjusted_p_value,
                      verdict_code=excluded.verdict_code,reason_code=excluded.reason_code,
                      trust_state=excluded.trust_state,source_version=excluded.source_version,updated_at=now()""",
                    (str(trial_id),str(hypothesis_id),execution_run_id,candidate["candidate_hash"],candidate["engine_code"],
                     result["symbol"],result["timeframe"],str(parameter_run["parameter_space_run_id"]),
                     result["validation_trades"],result["oos_trades"],result["oos_profit_factor"],result["oos_expectancy"],
                     result["folds_passed"],result["adjusted_p_value"],trial_state,result["verdict_code"],
                     result["reason_code"],trust_state,SOURCE_VERSION))
                cur.execute("""UPDATE analytics.canonical_hypothesis_registry_v1 SET lifecycle_state=%s,updated_at=now()
                    WHERE hypothesis_id=%s""", ("TESTED" if trial_state == "COMPLETE" else "UNVERIFIED", str(hypothesis_id)))

    print(f"parameter_space_run_id={parameter_run['parameter_space_run_id']}")
    print(f"execution_run_id={execution_run_id or 'NONE'}")
    print(f"canonical_hypotheses={len(candidates)}")
    print(f"linked_trials={linked_results}")
    print("promotion_allowed=0")
    print("paper_created=0")
    print("live_allowed=0")
    print("VERDICT=CANONICAL_HYPOTHESIS_TRIAL_REGISTRY_V2_OK")


if __name__ == "__main__":
    main()
