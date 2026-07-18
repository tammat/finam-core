from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
CONTRACT = "METHODOLOGY_V1_STRICT"
NAMESPACE = uuid.UUID("1d9a3a47-e61c-4d97-9443-bc4f0104dc22")
EXECUTION_KEYS = {"transaction_cost_bps","commission","slippage","reference_symbol",
                  "contract_symbol","contract_root","contract_expiration","adaptive_scenario_id",
                  "execution_policy"}


def parameter_core(parameters: dict) -> dict:
    return {key:value for key,value in parameters.items() if key not in EXECUTION_KEYS}


def parameter_hash(parameters: dict) -> str:
    raw = json.dumps(parameter_core(parameters),sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def bh_q_values(p_values: list[float]) -> list[float]:
    count = len(p_values)
    ordered = sorted(enumerate(p_values),key=lambda item:item[1])
    result = [1.0] * count
    running = 1.0
    for reverse_index in range(count-1,-1,-1):
        original,p_value = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running,p_value * count / rank)
        result[original] = min(1.0,running)
    return result


def are_neighbors(left: dict, right: dict) -> bool:
    keys = sorted(set(left).union(right))
    differences = sum(left.get(key) != right.get(key) for key in keys)
    return 0 < differences <= 1


def correlation(left: dict[str,float], right: dict[str,float]) -> tuple[float | None,int]:
    dates = sorted(set(left).intersection(right))
    if len(dates) < 2:
        return None,len(dates)
    a,b = [left[d] for d in dates],[right[d] for d in dates]
    if statistics.pstdev(a) == 0 or statistics.pstdev(b) == 0:
        return 0.0,len(dates)
    return statistics.correlation(a,b),len(dates)


def portfolio_daily_pnl(cursor) -> tuple[dict[str,float],bool]:
    cursor.execute("SELECT EXISTS(SELECT 1 FROM analytics.paper_portfolio_mtm_v1 WHERE paper_status='ACTIVE') active")
    active = bool(cursor.fetchone()["active"])
    cursor.execute("""
      WITH latest AS (
        SELECT date(mtm_ts) AS mtm_day,candidate_id,net_pnl,
               row_number() OVER(PARTITION BY date(mtm_ts),candidate_id ORDER BY mtm_ts DESC,id DESC) rn
        FROM analytics.paper_portfolio_mtm_v1 WHERE paper_status='ACTIVE'
      ), totals AS (
        SELECT mtm_day,sum(net_pnl)::float8 AS value
        FROM latest WHERE rn=1 GROUP BY mtm_day
      ) SELECT mtm_day,value FROM totals ORDER BY mtm_day
    """)
    rows = cursor.fetchall()
    result = {}
    previous = None
    for row in rows:
        value = float(row["value"])
        if previous is not None:
            result[row["mtm_day"].isoformat()] = value-previous
        previous = value
    return result,active


def main() -> int:
    scenario_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    search_run_id = os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"]
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT policy FROM analytics.edge_methodology_contract_v1 WHERE contract_code=%s AND active",(CONTRACT,))
            contract_row = cursor.fetchone()
            if not contract_row:
                raise RuntimeError("METHODOLOGY_CONTRACT_NOT_ACTIVE")
            policy = contract_row["policy"]
            cursor.execute("""SELECT policy_code,policy FROM analytics.execution_simulation_policy_v1
                WHERE active ORDER BY activated_at DESC LIMIT 1""")
            execution_contract = cursor.fetchone()
            if not execution_contract:
                raise RuntimeError("EXECUTION_SIMULATION_POLICY_NOT_ACTIVE")
            execution_policy = execution_contract["policy"]
            cursor.execute("SELECT * FROM analytics.walkforward_edge_search_v3 WHERE search_run_id=%s ORDER BY result_id",(search_run_id,))
            rows = cursor.fetchall()
            if not rows:
                raise RuntimeError("METHODOLOGY_WALKFORWARD_RESULTS_MISSING")
            q_values = bh_q_values([float(row["methodology_evidence"].get("one_sided_p_value",1.0)) for row in rows])
            portfolio,portfolio_exists = portfolio_daily_pnl(cursor)
            passed = 0
            for index,row in enumerate(rows):
                core = parameter_core(row["parameter_json"])
                p_hash = parameter_hash(row["parameter_json"])
                neighbors = sum(1 for other in rows if other["result_id"] != row["result_id"]
                    and other["strategy_family"] == row["strategy_family"] and other["symbol"] == row["symbol"]
                    and are_neighbors(core,parameter_core(other["parameter_json"]))
                    and float(other["net_profit_factor"]) >= float(policy["neighbor_min_profit_factor"])
                    and float(other["net_expectancy"]) > 0
                    and int(other["folds_passed"]) >= int(policy["neighbor_min_folds"]))
                fold5 = next((item for item in row["fold_metrics"] if int(item["fold"]) == 5),None)
                evaluation_id = uuid.uuid5(NAMESPACE,f"{scenario_run_id}:{row['result_id']}:{CONTRACT}")
                cursor.execute("""SELECT EXISTS(SELECT 1 FROM analytics.edge_holdout_consumption_v1
                    WHERE strategy_code=%s AND symbol=%s AND timeframe=%s AND parameter_hash=%s
                      AND holdout_end=%s AND evaluation_id<>%s) consumed""",
                    (row["strategy_code"],row["symbol"],row["timeframe"],p_hash,fold5["end"] if fold5 else None,str(evaluation_id)))
                consumed = bool(cursor.fetchone()["consumed"])
                evidence = row["methodology_evidence"]
                candidate_daily = {item["date"]:float(item["pnl"]) for item in evidence.get("daily_pnl",[])}
                portfolio_corr,overlap = correlation(candidate_daily,portfolio)
                statistical = q_values[index] <= float(policy["max_fdr_q"])
                robustness = neighbors >= int(policy["min_robust_neighbors"])
                holdout = bool(fold5 and fold5["passed"] and not consumed)
                execution = (
                    float(evidence.get("stressed_profit_factor",0)) >= float(policy["stress_min_profit_factor"])
                    and float(evidence.get("stressed_expectancy",0)) > 0
                    and int(evidence.get("signal_latency_bars",0)) >= int(execution_policy["signal_latency_bars"])
                    and float(evidence.get("average_fill_ratio",0)) >= float(execution_policy["minimum_fill_ratio"])
                    and float(evidence.get("fallback_quote_share",1)) <= float(execution_policy["max_fallback_quote_share"])
                    and float(evidence.get("contract_spec_coverage",0)) >= 1.0
                )
                capacity = float(evidence.get("capacity_rub",0)) >= float(policy["min_capacity_rub"])
                portfolio_pass = (not portfolio_exists) or (overlap >= int(policy["min_portfolio_overlap_days"])
                    and portfolio_corr is not None and abs(portfolio_corr) <= float(policy["max_portfolio_abs_correlation"]))
                base_pass = row["verdict_code"] == "OOS_PASS"
                gates = {"STATISTICAL_SIGNIFICANCE":statistical,"PARAMETER_ROBUSTNESS":robustness,
                         "INDEPENDENT_HOLDOUT":holdout,"REALISTIC_EXECUTION":execution,
                         "CAPACITY":capacity,"PORTFOLIO_CONTRIBUTION":portfolio_pass}
                verdict = "PASS" if base_pass and all(gates.values()) else "FAIL"
                reasons = (["BASE_WALKFORWARD_FAILED"] if not base_pass else []) + [key for key,value in gates.items() if not value]
                audit = {**evidence,"base_walkforward_pass":base_pass,"portfolio_overlap_days":overlap,
                         "empty_portfolio":not portfolio_exists,"contract_policy":policy,
                         "execution_policy_code":execution_contract["policy_code"],
                         "execution_policy":execution_policy}
                cursor.execute("""INSERT INTO analytics.edge_methodology_evaluation_v1
                  (evaluation_id,scenario_run_id,search_run_id,result_id,contract_code,algorithm_code,
                   strategy_code,symbol,timeframe,parameter_core,parameter_hash,statistical_pass,
                   robustness_pass,holdout_pass,execution_pass,capacity_pass,portfolio_pass,fdr_q,
                   robust_neighbors,stressed_profit_factor,capacity_rub,portfolio_correlation,evidence,
                   reason_codes,verdict_code,promotion_allowed)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false)
                  ON CONFLICT(scenario_run_id,result_id) DO UPDATE SET
                    statistical_pass=EXCLUDED.statistical_pass,robustness_pass=EXCLUDED.robustness_pass,
                    holdout_pass=EXCLUDED.holdout_pass,execution_pass=EXCLUDED.execution_pass,
                    capacity_pass=EXCLUDED.capacity_pass,portfolio_pass=EXCLUDED.portfolio_pass,
                    fdr_q=EXCLUDED.fdr_q,robust_neighbors=EXCLUDED.robust_neighbors,
                    stressed_profit_factor=EXCLUDED.stressed_profit_factor,capacity_rub=EXCLUDED.capacity_rub,
                    portfolio_correlation=EXCLUDED.portfolio_correlation,evidence=EXCLUDED.evidence,
                    reason_codes=EXCLUDED.reason_codes,verdict_code=EXCLUDED.verdict_code""",
                    (str(evaluation_id),scenario_run_id,search_run_id,str(row["result_id"]),CONTRACT,
                     row["strategy_family"],row["strategy_code"],row["symbol"],row["timeframe"],
                     psycopg2.extras.Json(core),p_hash,statistical,robustness,holdout,execution,capacity,
                     portfolio_pass,q_values[index],neighbors,evidence.get("stressed_profit_factor",0),
                     evidence.get("capacity_rub",0),portfolio_corr,psycopg2.extras.Json(audit),
                     psycopg2.extras.Json(reasons),verdict))
                if verdict == "PASS" and fold5:
                    consumption_id=uuid.uuid5(NAMESPACE,f"{evaluation_id}:{fold5['end']}")
                    cursor.execute("""INSERT INTO analytics.edge_holdout_consumption_v1
                      (consumption_id,evaluation_id,strategy_code,symbol,timeframe,parameter_hash,holdout_end)
                      VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                      (str(consumption_id),str(evaluation_id),row["strategy_code"],row["symbol"],row["timeframe"],p_hash,fold5["end"]))
                passed += int(verdict == "PASS")
    print(f"methodology_evaluated={len(rows)}")
    print(f"methodology_pass={passed}")
    print("all_gates_required=1")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=EDGE_METHODOLOGY_CONTRACT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
