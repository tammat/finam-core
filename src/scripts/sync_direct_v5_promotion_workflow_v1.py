from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "DIRECT_V5_PROMOTION_WORKFLOW_SYNC_V1"


def _symbol_group(strategy_code: str, logical_symbol: str) -> str:
    return {
        "BR_CONSERVATIVE_BREAKOUT": "BR",
        "NG_CONSERVATIVE_BREAKOUT_M1": "NG",
        "CNY_REGIME_FUTURES": "CNY",
        "USD_REGIME_FUTURES": "USD",
        "GOLD_TREND_BREAKOUT": "GOLD",
    }.get(strategy_code, logical_symbol.split("@", 1)[0])


def _workflow_stage(oos_status: str) -> str:
    return {
        "OOS_PASS": "V5_OOS_PASS",
        "OOS_FAIL": "V5_OOS_FAILED",
    }.get(oos_status, "V5_OOS_COLLECTING")


def main() -> int:
    synced = passed = failed = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(184007) AS locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=DIRECT_V5_PROMOTION_WORKFLOW_SYNC_ALREADY_RUNNING")
                return 0
            cursor.execute("""
                SELECT r.*,v.run_id,v.status_code AS oos_status,
                       v.observations_included,v.observations_excluded,
                       v.expectancy,v.profit_factor,v.reason_code AS oos_reason
                FROM analytics.v5_post_fix_branch_registry_v1 r
                JOIN analytics.v5_oos_run_v1 v ON v.admission_id=r.admission_id
                WHERE r.methodology_epoch='POST_FIX_V1'
                  AND r.state_code<>'RETIRED'
                ORDER BY r.branch_code
            """)
            for row in cursor.fetchall():
                stage = _workflow_stage(str(row["oos_status"]))
                evidence = {
                    "source_version": SOURCE_VERSION,
                    "branch_code": row["branch_code"],
                    "methodology_epoch": row["methodology_epoch"],
                    "direct_v5_preregistered": True,
                    "historical_statistical_pass_claimed": False,
                    "historical_expensive_gates_pass_claimed": False,
                    "paper_requires_strict_frozen_v5_oos_pass": True,
                    "paper_risk_fraction": 0.25,
                    "real_allowed": False,
                    "oos": {
                        "status": row["oos_status"],
                        "included": int(row["observations_included"] or 0),
                        "excluded": int(row["observations_excluded"] or 0),
                        "minimum": int(row["minimum_observations"]),
                        "expectancy": (str(row["expectancy"]) if row["expectancy"] is not None else None),
                        "profit_factor": (str(row["profit_factor"]) if row["profit_factor"] is not None else None),
                        "reason": row["oos_reason"],
                    },
                }
                cursor.execute("""
                    INSERT INTO analytics.entry_exit_promotion_workflow_v1(
                        strategy_code,symbol_group,side_code,candidate_code,
                        workflow_stage,statistical_verdict,expensive_gates_pass,
                        v5_oos_pass,paper_risk_fraction,evidence,admission_id,oos_run_id,
                        first_entered_at,last_transition_at,updated_at)
                    VALUES(%s,%s,%s,%s,%s,'ACCUMULATE',false,%s,.25,%s::jsonb,%s,%s,
                           clock_timestamp(),clock_timestamp(),clock_timestamp())
                    ON CONFLICT(strategy_code,symbol_group,side_code,candidate_code)
                    DO UPDATE SET
                        workflow_stage=excluded.workflow_stage,
                        statistical_verdict='ACCUMULATE',
                        expensive_gates_pass=false,
                        v5_oos_pass=excluded.v5_oos_pass,
                        paper_risk_fraction=.25,
                        evidence=excluded.evidence,
                        admission_id=excluded.admission_id,
                        oos_run_id=excluded.oos_run_id,
                        first_entered_at=CASE
                          WHEN analytics.entry_exit_promotion_workflow_v1.workflow_stage
                               IS DISTINCT FROM excluded.workflow_stage
                          THEN clock_timestamp()
                          ELSE analytics.entry_exit_promotion_workflow_v1.first_entered_at END,
                        last_transition_at=CASE
                          WHEN analytics.entry_exit_promotion_workflow_v1.workflow_stage
                               IS DISTINCT FROM excluded.workflow_stage
                          THEN clock_timestamp()
                          ELSE analytics.entry_exit_promotion_workflow_v1.last_transition_at END,
                        updated_at=clock_timestamp()
                """, (
                    row["strategy_code"],
                    _symbol_group(str(row["strategy_code"]), str(row["logical_symbol"])),
                    row["side_code"], row["candidate_code"], stage,
                    stage == "V5_OOS_PASS", json.dumps(evidence),
                    row["admission_id"], row["run_id"],
                ))
                synced += 1
                passed += stage == "V5_OOS_PASS"
                failed += stage == "V5_OOS_FAILED"
    print(f"direct_v5_workflows_synced={synced}")
    print(f"direct_v5_oos_pass={passed}")
    print(f"direct_v5_oos_fail={failed}")
    print("paper_activation_requires_strict_v5_pass=1 real_allowed=0")
    print(f"VERDICT={SOURCE_VERSION}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
