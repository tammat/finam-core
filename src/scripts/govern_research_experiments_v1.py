from __future__ import annotations

import hashlib
import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
NAMESPACE = uuid.UUID("d41c18a5-2584-4292-b46d-75d40474bf1a")
EXECUTION_KEYS = {"transaction_cost_bps", "commission", "slippage", "reference_symbol",
                  "contract_symbol", "contract_root", "contract_expiration", "adaptive_scenario_id",
                  "execution_policy"}


def parameter_hash(parameters: dict) -> str:
    core = {key: value for key, value in parameters.items() if key not in EXECUTION_KEYS}
    raw = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def asset_class(symbol: str) -> str:
    if symbol.endswith("@RTSX"):
        return "FUTURES"
    if symbol.endswith("@MISX"):
        return "EQUITY"
    if symbol.endswith("USD"):
        return "CRYPTO"
    return "OTHER"


def main() -> int:
    scenario_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    search_run_id = os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"]
    inserted = global_pass = holdout_ready = holdout_reused = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT count(*) AS count FROM analytics.research_global_experiment_v1")
            prior_trials = int(cursor.fetchone()["count"])
            cursor.execute("""SELECT * FROM analytics.walkforward_edge_search_v3
                WHERE search_run_id=%s ORDER BY result_id""", (search_run_id,))
            rows = cursor.fetchall()
            holdout_access: dict[tuple[str, str, str, str], str] = {}
            for row in rows:
                fold5 = next((item for item in row["fold_metrics"] if int(item["fold"]) == 5), None)
                if not fold5:
                    access = "MISSING"
                else:
                    key = (row["symbol"], row["timeframe"], fold5["start"], fold5["end"])
                    if key not in holdout_access:
                        cursor.execute("""SELECT holdout_id FROM analytics.research_holdout_snapshot_v1
                            WHERE symbol=%s AND timeframe=%s AND owner_search_run_id<>%s
                              AND tstzrange(holdout_start,holdout_end,'[]') && tstzrange(%s,%s,'[]')
                            LIMIT 1""", (row["symbol"], row["timeframe"], search_run_id,
                                         fold5["start"], fold5["end"]))
                        if cursor.fetchone():
                            access = "REUSED_BLOCKED"
                        else:
                            holdout_id = uuid.uuid5(NAMESPACE, f"{search_run_id}:{key}")
                            cursor.execute("""INSERT INTO analytics.research_holdout_snapshot_v1
                                (holdout_id,owner_search_run_id,symbol,timeframe,holdout_start,holdout_end,data_watermark)
                                VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                                (str(holdout_id),search_run_id,row["symbol"],row["timeframe"],
                                 fold5["start"],fold5["end"],fold5["end"]))
                            access = "OPENED"
                        holdout_access[key] = access
                    access = holdout_access[key]
                holdout_ready += int(access == "OPENED")
                holdout_reused += int(access == "REUSED_BLOCKED")

                cursor.execute("""SELECT experiment_no,adjusted_p_value FROM analytics.research_global_experiment_v1
                    WHERE scenario_run_id=%s AND result_id=%s""", (scenario_run_id, row["result_id"]))
                existing = cursor.fetchone()
                raw_p = min(1.0, max(0.0, float((row["methodology_evidence"] or {}).get("one_sided_p_value", 1))))
                if existing:
                    experiment_no = int(existing["experiment_no"])
                    adjusted = float(existing["adjusted_p_value"])
                else:
                    cumulative = prior_trials + inserted + 1
                    adjusted = min(1.0, raw_p * cumulative)
                    experiment_id = uuid.uuid5(NAMESPACE, f"{scenario_run_id}:{row['result_id']}")
                    verdict = "PASS" if adjusted <= 0.10 else "FAIL"
                    cursor.execute("""INSERT INTO analytics.research_global_experiment_v1
                        (experiment_id,scenario_run_id,search_run_id,result_id,asset_class,hypothesis_code,
                         strategy_code,symbol,timeframe,parameter_hash,raw_p_value,cumulative_trials,
                         adjusted_p_value,verdict_code,reason_code)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING experiment_no""",
                        (str(experiment_id),scenario_run_id,search_run_id,str(row["result_id"]),
                         asset_class(row["symbol"]),row["strategy_family"],row["strategy_code"],
                         row["symbol"],row["timeframe"],parameter_hash(row["parameter_json"]),raw_p,
                         cumulative,adjusted,verdict,
                         "GLOBAL_MULTIPLE_TEST_PASS" if verdict == "PASS" else "GLOBAL_MULTIPLE_TEST_FAIL"))
                    experiment_no = int(cursor.fetchone()["experiment_no"])
                    inserted += 1
                cursor.execute("""UPDATE analytics.walkforward_edge_search_v3
                    SET methodology_evidence=methodology_evidence || %s::jsonb WHERE result_id=%s""",
                    (json.dumps({"global_experiment_no": experiment_no,
                                 "global_adjusted_p_value": adjusted,
                                 "holdout_access_code": access}), str(row["result_id"])))
            cursor.execute("SELECT count(*) AS count FROM analytics.research_global_experiment_v1")
            cumulative_trials = int(cursor.fetchone()["count"])
            cursor.execute("""UPDATE analytics.research_global_experiment_v1
                SET cumulative_trials=%s,
                    adjusted_p_value=least(1::numeric,raw_p_value*%s),
                    verdict_code=CASE WHEN least(1::numeric,raw_p_value*%s)<=0.10 THEN 'PASS' ELSE 'FAIL' END,
                    reason_code=CASE WHEN least(1::numeric,raw_p_value*%s)<=0.10
                      THEN 'GLOBAL_MULTIPLE_TEST_PASS' ELSE 'GLOBAL_MULTIPLE_TEST_FAIL' END""",
                (cumulative_trials,cumulative_trials,cumulative_trials,cumulative_trials))
            cursor.execute("""UPDATE analytics.walkforward_edge_search_v3 w
                SET methodology_evidence=w.methodology_evidence || jsonb_build_object(
                    'global_experiment_no',g.experiment_no,
                    'global_adjusted_p_value',g.adjusted_p_value)
                FROM analytics.research_global_experiment_v1 g
                WHERE g.search_run_id=%s AND g.result_id=w.result_id""", (search_run_id,))
            cursor.execute("""SELECT count(*) AS count FROM analytics.research_global_experiment_v1
                WHERE scenario_run_id=%s AND verdict_code='PASS'""", (scenario_run_id,))
            global_pass = int(cursor.fetchone()["count"])
    print(f"global_experiments_registered={inserted}")
    print(f"global_significance_pass={global_pass}")
    print(f"holdout_opened={holdout_ready}")
    print(f"holdout_reuse_blocked={holdout_reused}")
    print("VERDICT=RESEARCH_EXPERIMENT_GOVERNANCE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
