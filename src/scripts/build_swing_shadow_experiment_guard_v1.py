from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "SWING_SHADOW_EXPERIMENT_GUARD_V1"
NAMESPACE = uuid.UUID("5b16d86d-1536-480f-ab3d-d757d6bbf9e6")
ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(
    os.getenv(
        "SWING_FORWARD_SHADOW_POLICY_CONFIG",
        ROOT / "config/research/swing_forward_shadow_policy_v1.json",
    )
)


def load_policy() -> dict:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("policy_version") != "SWING_FORWARD_SHADOW_POLICY_V1":
        raise RuntimeError("SWING_FORWARD_SHADOW_POLICY_VERSION_INVALID")
    return policy

DDL = """
CREATE TABLE IF NOT EXISTS analytics.swing_shadow_cohort_v1 (
    swing_shadow_cohort_id uuid NOT NULL,
    swing_shadow_candidate_id uuid NOT NULL,
    factory_run_id uuid NOT NULL,
    validation_run_id uuid NOT NULL,
    hypothesis_id uuid NOT NULL,
    strategy_family text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    frozen_parameter_json jsonb NOT NULL,
    selection_pf numeric NOT NULL,
    validation_pf numeric NOT NULL,
    validation_expectancy numeric NOT NULL,
    validation_folds_passed integer NOT NULL,
    adjusted_p_value numeric NOT NULL,
    validation_status text NOT NULL,
    observation_not_before timestamptz NOT NULL,
    cohort_status text NOT NULL,
    shadow_only boolean NOT NULL DEFAULT true,
    paper_allowed boolean NOT NULL DEFAULT false,
    live_allowed boolean NOT NULL DEFAULT false,
    final_oos_opened boolean NOT NULL DEFAULT false,
    criteria_json jsonb NOT NULL,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY(swing_shadow_cohort_id,swing_shadow_candidate_id),
    UNIQUE(swing_shadow_cohort_id,hypothesis_id)
);
CREATE TABLE IF NOT EXISTS analytics.swing_shadow_guard_check_v1 (
    guard_check_id bigserial PRIMARY KEY,
    swing_shadow_cohort_id uuid NOT NULL,
    check_status text NOT NULL,
    candidates integer NOT NULL,
    validation_passed integer NOT NULL,
    final_oos_opened integer NOT NULL,
    data_quality_ready integer NOT NULL,
    data_quality_total integer NOT NULL,
    observations integer NOT NULL,
    unsafe_rows integer NOT NULL,
    reasons_json jsonb NOT NULL,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
"""


def main() -> int:
    criteria = load_policy()
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute("SELECT swing_shadow_cohort_id FROM analytics.swing_shadow_cohort_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cur.fetchone()
            if latest:
                cohort_id = latest["swing_shadow_cohort_id"]
            else:
                cur.execute("SELECT validation_run_id,factory_run_id FROM analytics.swing_selection_validation_result_v1 ORDER BY created_at DESC LIMIT 1")
                run = cur.fetchone()
                if not run:
                    raise RuntimeError("SWING_VALIDATION_RUN_REQUIRED")
                cohort_id = uuid.uuid5(NAMESPACE, f"{run['validation_run_id']}:SWING_SHADOW_V1")
                cur.execute("""
                    WITH ranked AS (
                        SELECT r.*,f.parameter_json,
                               row_number() OVER (PARTITION BY r.timeframe,r.strategy_family ORDER BY
                                   (r.validation_status='VALIDATION_PASS') DESC,
                                   r.validation_folds_passed DESC,r.validation_pf DESC,
                                   r.adjusted_p_value,r.hypothesis_id) AS rank
                        FROM analytics.swing_selection_validation_result_v1 r
                        JOIN analytics.swing_hypothesis_factory_v1 f
                          ON f.factory_run_id=r.factory_run_id AND f.hypothesis_id=r.hypothesis_id
                        WHERE r.validation_run_id=%s AND r.final_oos_opened=false AND f.final_oos_opened=false
                    )
                    SELECT * FROM ranked WHERE rank=1 ORDER BY timeframe,strategy_family
                """, (run["validation_run_id"],))
                selected = cur.fetchall()
                if len(selected) != criteria["cohort_size"]:
                    raise RuntimeError(f"SWING_SHADOW_COHORT_SIZE_INVALID:{len(selected)}")
                for row in selected:
                    candidate_id = uuid.uuid5(NAMESPACE, f"{cohort_id}:{row['hypothesis_id']}")
                    cur.execute("""
                        INSERT INTO analytics.swing_shadow_cohort_v1 (
                            swing_shadow_cohort_id,swing_shadow_candidate_id,factory_run_id,validation_run_id,
                            hypothesis_id,strategy_family,symbol,timeframe,frozen_parameter_json,
                            selection_pf,validation_pf,validation_expectancy,validation_folds_passed,
                            adjusted_p_value,validation_status,observation_not_before,cohort_status,
                            shadow_only,paper_allowed,live_allowed,final_oos_opened,criteria_json,source_version
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,now(),'ACCUMULATING',true,false,false,false,%s::jsonb,%s)
                    """, (str(cohort_id),str(candidate_id),str(row["factory_run_id"]),str(row["validation_run_id"]),
                          str(row["hypothesis_id"]),row["strategy_family"],row["symbol"],row["timeframe"],
                          json.dumps(row["parameter_json"]),row["selection_pf"],row["validation_pf"],
                          row["validation_expectancy"],row["validation_folds_passed"],row["adjusted_p_value"],
                          row["validation_status"],json.dumps(criteria),SOURCE_VERSION))

            cur.execute("""SELECT count(*) candidates,count(*) FILTER(WHERE validation_status='VALIDATION_PASS') validation_passed,
                       count(*) FILTER(WHERE final_oos_opened) final_oos_opened,
                       count(*) FILTER(WHERE NOT shadow_only OR paper_allowed OR live_allowed) unsafe
                FROM analytics.swing_shadow_cohort_v1 WHERE swing_shadow_cohort_id=%s""", (str(cohort_id),))
            cohort = dict(cur.fetchone())
            cur.execute("SELECT audit_run_id FROM analytics.swing_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1")
            audit = cur.fetchone()
            cur.execute("SELECT count(*) total,count(*) FILTER(WHERE quality_status='READY') ready FROM analytics.swing_data_quality_gate_v1 WHERE audit_run_id=%s", (audit["audit_run_id"],))
            quality = dict(cur.fetchone())
            cur.execute("SELECT to_regclass('analytics.swing_shadow_observation_v1') AS table_name")
            observations = 0
            if cur.fetchone()["table_name"]:
                cur.execute("SELECT count(*) observations FROM analytics.swing_shadow_observation_v1 WHERE swing_shadow_cohort_id=%s", (str(cohort_id),))
                observations = int(cur.fetchone()["observations"])
            reasons = []
            if int(cohort["candidates"]) != criteria["cohort_size"]: reasons.append("COHORT_SIZE_INVALID")
            if int(cohort["final_oos_opened"]): reasons.append("FINAL_OOS_OPENED")
            if int(cohort["unsafe"]): reasons.append("UNSAFE_FLAGS")
            if int(quality["ready"]) != int(quality["total"]): reasons.append("DATA_QUALITY_NOT_READY")
            status = "READY_FOR_SWING_SHADOW" if not reasons else "BLOCKED"
            cur.execute("""INSERT INTO analytics.swing_shadow_guard_check_v1
                (swing_shadow_cohort_id,check_status,candidates,validation_passed,final_oos_opened,
                 data_quality_ready,data_quality_total,observations,unsafe_rows,reasons_json,source_version)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)""",
                (str(cohort_id),status,cohort["candidates"],cohort["validation_passed"],cohort["final_oos_opened"],
                 quality["ready"],quality["total"],observations,cohort["unsafe"],json.dumps(reasons),SOURCE_VERSION))

    print(f"cohort_id={cohort_id}")
    print(f"status={status}")
    print(f"candidates={cohort['candidates']}")
    print(f"validation_passed={cohort['validation_passed']}")
    print(f"final_oos_opened={cohort['final_oos_opened']}")
    print(f"data_quality={quality['ready']}/{quality['total']}")
    print(f"observations={observations}")
    print(f"unsafe={cohort['unsafe']}")
    print(f"reasons={','.join(reasons) if reasons else 'NONE'}")
    print("paper_allowed=0")
    print("live_allowed=0")
    print("VERDICT=SWING_SHADOW_EXPERIMENT_GUARD_V1_OK")
    return 0 if status == "READY_FOR_SWING_SHADOW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
