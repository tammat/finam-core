from __future__ import annotations

import hashlib
import itertools
import json
import os
import uuid
from collections import Counter
from datetime import datetime

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "NEXT_EDGE_RESEARCH_PLAN_V2_METHODOLOGY_FAIL_DRIVEN"
NAMESPACE = uuid.UUID("33eab308-54f5-47ad-a9ae-f7f42ac19fa7")
MIN_FUTURE_BARS = int(os.getenv("ADAPTIVE_EDGE_MIN_FUTURE_BARS", "500"))
MAX_NEW_SCENARIOS = int(os.getenv("ADAPTIVE_EDGE_MAX_NEW_SCENARIOS", "3"))
MAX_VARIANTS_PER_ITEM = int(os.getenv("EDGE_NEXT_PLAN_MAX_VARIANTS", "48"))


REASON_POLICY = {
    "INSUFFICIENT_TRADES": ("EXPAND_SIGNAL_FREQUENCY", 4, "Увеличить частоту сигналов в допустимых границах."),
    "NEGATIVE_COST_ADJUSTED_EXPECTANCY": ("STRENGTHEN_ENTRY_SHORTEN_HOLD", 3, "Усилить вход и сократить удержание без изменения издержек."),
    "PROFIT_FACTOR_BELOW_GATE": ("LOCAL_PARAMETER_NEIGHBORHOOD", 2, "Проверить ближайшую область параметров при прежнем PASS."),
    "WALKFORWARD_FOLDS_UNSTABLE": ("REFINE_REGIME_CONTRACT", 1, "Разделить режимы рынка и проверить устойчивость фолдов."),
    "FINAL_HOLDOUT_FAILED": ("ORTHOGONAL_FUTURE_ONLY", 5, "Исключить прежний fingerprint и проверять только будущие данные."),
    "METHODOLOGY_REALISTIC_EXECUTION": ("STRENGTHEN_SIGNAL_SAME_COSTS", 1, "Усилить сигнал и сохранить полную модель издержек."),
    "METHODOLOGY_STATISTICAL_SIGNIFICANCE": ("EXPAND_FUTURE_EVIDENCE", 2, "Накопить больше независимых будущих наблюдений."),
    "METHODOLOGY_PARAMETER_ROBUSTNESS": ("LOCAL_PARAMETER_NEIGHBORHOOD", 3, "Проверить соседние параметры без выбора единичного пика."),
    "METHODOLOGY_INDEPENDENT_HOLDOUT": ("NEW_CLEAN_HOLDOUT", 4, "Использовать только новую, ранее не потреблённую выборку."),
    "METHODOLOGY_CAPACITY": ("LIQUIDITY_PEER_MARKET", 5, "Проверить ту же гипотезу на более ликвидном инструменте-аналогe."),
    "METHODOLOGY_PORTFOLIO_CONTRIBUTION": ("DIVERSIFY_MARKET_EXPOSURE", 6, "Проверить гипотезу на другом ликвидном рынке для снижения корреляции."),
}


def gate_hash(gate_policy: dict) -> str:
    canonical = json.dumps(gate_policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    # PostgreSQL jsonb::text differs in whitespace, so DB stores its own md5 expression.
    return hashlib.sha256(canonical.encode()).hexdigest()


def development_metrics(folds: list[dict]) -> dict | None:
    """Fold 5 is a consumed holdout and is deliberately excluded from selection."""
    development = [item for item in folds if int(item["fold"]) in (1, 2, 3, 4)]
    if len(development) != 4:
        return None
    trades = sum(int(item["trades"]) for item in development)
    if not trades:
        return None
    weighted_pf = sum(float(item["profit_factor"]) * int(item["trades"]) for item in development) / trades
    weighted_expectancy = sum(float(item["expectancy"]) * int(item["trades"]) for item in development) / trades
    return {"selection_folds": [1, 2, 3, 4], "trades": trades,
            "weighted_profit_factor": round(weighted_pf, 8),
            "weighted_expectancy": round(weighted_expectancy, 8),
            "folds_passed": sum(bool(item["passed"]) for item in development)}


def _number_set(value: float, ratios: tuple[float, ...], minimum: float, integer: bool = False) -> list:
    values = {max(minimum, value * ratio) for ratio in ratios}
    return sorted({int(round(item)) if integer else round(item, 4) for item in values})


def adapted_grid(base_grid: list[dict], reason: str, algorithm_code: str = "", budget: int = MAX_VARIANTS_PER_ITEM) -> list[dict]:
    """Change hypotheses, never validation/OOS/walk-forward gates or cost inputs."""
    output: list[dict] = []
    for base in base_grid:
        clean = {key: value for key, value in base.items() if key not in {
            "commission", "slippage", "transaction_cost_bps", "adaptive_scenario_id"
        }}
        lookback, hold, threshold = int(clean["lookback"]), int(clean["hold"]), float(clean["threshold"])
        if reason in {"INSUFFICIENT_TRADES", "METHODOLOGY_STATISTICAL_SIGNIFICANCE"}:
            lookbacks, holds, thresholds = _number_set(lookback, (.5, .75, 1), 10, True), _number_set(hold, (.65, 1), 2, True), _number_set(threshold, (.65, .8, 1), 0)
        elif reason in {"NEGATIVE_COST_ADJUSTED_EXPECTANCY", "METHODOLOGY_REALISTIC_EXECUTION"}:
            lookbacks, holds, thresholds = _number_set(lookback, (.75, 1, 1.25), 10, True), _number_set(hold, (.5, .75, 1), 2, True), _number_set(threshold, (1, 1.2, 1.5), 0)
        elif reason == "WALKFORWARD_FOLDS_UNSTABLE":
            lookbacks, holds, thresholds = _number_set(lookback, (.8, 1, 1.2), 10, True), [hold], _number_set(threshold, (.9, 1, 1.1), 0)
        elif reason in {"FINAL_HOLDOUT_FAILED", "METHODOLOGY_INDEPENDENT_HOLDOUT"}:
            if reason == "METHODOLOGY_INDEPENDENT_HOLDOUT":
                output.append(clean)
                continue
            lookbacks, holds, thresholds = _number_set(lookback, (.6, 1.4), 10, True), _number_set(hold, (.6, 1.4), 2, True), _number_set(threshold, (.75, 1.35), 0)
        else:
            lookbacks, holds, thresholds = _number_set(lookback, (.75, 1, 1.25), 10, True), _number_set(hold, (.75, 1, 1.25), 2, True), _number_set(threshold, (.9, 1, 1.15), 0)
        for lb, hd, th in itertools.product(lookbacks, holds, thresholds):
            candidate = {**clean, "lookback": lb, "hold": hd, "threshold": th}
            if algorithm_code == "DONCHIAN_VOL_BREAKOUT":
                candidate.update({"exit_policy_code": "DYNAMIC_EXIT_V1", "exit_max_holding_bars": 20,
                                  "exit_trend_lookback": 5, "exit_volatility_risk_multiplier": 2.0,
                                  "entry_policy_code": "META_ENTRY_V2", "entry_trend_mode": "WITH_TREND",
                                  "entry_volume_mode": "REQUIRE"})
            elif algorithm_code == "EMA_TREND":
                candidate.update({"entry_policy_code": "META_ENTRY_V2",
                                  "entry_trend_mode": "WITH_TREND",
                                  "entry_min_volatility_bps": 1.0,
                                  "entry_max_volatility_bps": 120.0,
                                  "entry_volume_mode": "REQUIRE",
                                  "session_analysis": "MARKET_SESSION_CONTRACT_V1",
                                  "exit_policy_code": "DYNAMIC_EXIT_V1",
                                  "exit_max_holding_bars": 20,
                                  "exit_trend_lookback": 5,
                                  "exit_volatility_risk_multiplier": 2.0})
            if candidate not in output:
                output.append(candidate)
            if len(output) >= min(MAX_VARIANTS_PER_ITEM, budget):
                return output
    return output


def priority_score(row: dict) -> tuple:
    metrics = row["best_metrics"] or {}
    reason_rank = REASON_POLICY.get(row["primary_reason_code"], ("RESEARCH_NEW_FAMILY", 9, ""))[1]
    return (int(row.get("compute_priority_rank", 100)), reason_rank,
            -int(metrics.get("folds", 0)), -float(metrics.get("profit_factor", 0)),
            -float(metrics.get("expectancy", 0)), row["algorithm_code"])


def methodology_failures(cursor, parent_run_id: str) -> list[dict]:
    cursor.execute("""
        SELECT m.evaluation_id AS methodology_evaluation_id,m.result_id,m.algorithm_code,
               m.strategy_code,m.symbol,m.parameter_core AS parameter_json,w.fold_metrics,
               r.parameter_grid,r.regime_policy,r.gate_policy,
               coalesce(p.priority_rank,100) compute_priority_rank,
               coalesce(p.coarse_budget,4) compute_budget,
               coalesce(p.promotion_blocked,false) promotion_blocked,
               jsonb_build_object('folds',w.folds_passed,'profit_factor',w.net_profit_factor,
                                  'expectancy',w.net_expectancy) AS best_metrics,
               CASE
                 WHEN NOT m.execution_pass THEN 'METHODOLOGY_REALISTIC_EXECUTION'
                 WHEN NOT m.statistical_pass THEN 'METHODOLOGY_STATISTICAL_SIGNIFICANCE'
                 WHEN NOT m.robustness_pass THEN 'METHODOLOGY_PARAMETER_ROBUSTNESS'
                 WHEN NOT m.holdout_pass THEN 'METHODOLOGY_INDEPENDENT_HOLDOUT'
                 WHEN NOT m.capacity_pass THEN 'METHODOLOGY_CAPACITY'
                 WHEN NOT m.portfolio_pass THEN 'METHODOLOGY_PORTFOLIO_CONTRIBUTION'
               END AS primary_reason_code
        FROM analytics.edge_methodology_evaluation_v1 m
        JOIN analytics.walkforward_edge_search_v3 w ON w.result_id=m.result_id
        JOIN analytics.edge_search_algorithm_registry_v1 r ON r.algorithm_code=m.algorithm_code
        LEFT JOIN analytics.edge_algorithm_compute_policy_v1 p ON p.algorithm_code=m.algorithm_code
        WHERE m.scenario_run_id=%s AND m.verdict_code='FAIL' AND r.enabled
          AND NOT coalesce(p.promotion_blocked,false) AND coalesce(p.coarse_budget,4)>0
          AND coalesce((m.evidence->>'base_walkforward_pass')::boolean,false)
        ORDER BY m.created_at,m.evaluation_id
    """, (parent_run_id,))
    return [dict(row) for row in cursor.fetchall()]


def liquid_peer(cursor, source_symbol: str) -> str:
    suffix = source_symbol.split("@",1)[1] if "@" in source_symbol else ""
    cursor.execute("""
      WITH liquidity AS (
        SELECT b.symbol,percentile_cont(.5) WITHIN GROUP(ORDER BY b.close*b.volume) score
        FROM public.market_bars b
        JOIN analytics.market_contract_spec_v1 s ON s.symbol=b.symbol AND s.is_active
        WHERE b.timeframe='M5' AND b.ts>=clock_timestamp()-interval '7 days'
          AND b.symbol<>%s AND (%s='' OR split_part(b.symbol,'@',2)=%s)
          AND b.close>0 AND b.volume>0
        GROUP BY b.symbol)
      SELECT symbol FROM liquidity ORDER BY score DESC NULLS LAST,symbol LIMIT 1
    """, (source_symbol,suffix,suffix))
    row=cursor.fetchone()
    return str(row["symbol"]) if row else source_symbol


def activate_ready(cursor) -> int:
    cursor.execute("""
        UPDATE analytics.edge_search_adaptive_scenario_v1 s
        SET status_code='ACTIVE',reason_code='FUTURE_CONFIRMATION_WINDOW_READY',
            activated_at=clock_timestamp(),updated_at=clock_timestamp()
        WHERE s.status_code='WAITING_FUTURE_DATA'
          AND (SELECT count(*) FROM public.market_bars b WHERE b.symbol=s.target_symbol
               AND b.timeframe='M5' AND b.ts>s.confirmation_after_ts
               AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')) >= s.minimum_future_bars
        RETURNING adaptive_scenario_id
    """)
    ids = [str(row["adaptive_scenario_id"]) for row in cursor.fetchall()]
    if ids:
        cursor.execute("""UPDATE analytics.edge_next_research_plan_item_v1
            SET status_code='ACTIVE',updated_at=clock_timestamp()
            WHERE adaptive_scenario_id=ANY(%s::uuid[])""", (ids,))
    return len(ids)


def close_evaluated(cursor, search_run_id: str) -> int:
    cursor.execute("""
        WITH outcomes AS (
          SELECT s.adaptive_scenario_id,bool_or(w.verdict_code='OOS_PASS') AS passed
          FROM analytics.edge_search_adaptive_scenario_v1 s
          JOIN analytics.walkforward_edge_search_v3 w ON w.search_run_id=%s
           AND w.parameter_json->>'adaptive_scenario_id'=s.adaptive_scenario_id::text
          WHERE s.status_code='ACTIVE' GROUP BY s.adaptive_scenario_id
        ), changed AS (
          UPDATE analytics.edge_search_adaptive_scenario_v1 s
          SET status_code=CASE WHEN o.passed THEN 'EVALUATED_PASS' ELSE 'EVALUATED_FAIL' END,
              reason_code=CASE WHEN o.passed THEN 'FUTURE_DATA_PASS' ELSE 'FUTURE_DATA_NO_PASS' END,
              evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
          FROM outcomes o WHERE s.adaptive_scenario_id=o.adaptive_scenario_id
          RETURNING s.adaptive_scenario_id,s.status_code
        )
        UPDATE analytics.edge_next_research_plan_item_v1 i
        SET status_code=c.status_code,updated_at=clock_timestamp()
        FROM changed c WHERE i.adaptive_scenario_id=c.adaptive_scenario_id
        RETURNING i.plan_item_id
    """, (search_run_id,))
    return len(cursor.fetchall())


def sync_plan_statuses(cursor) -> None:
    cursor.execute("""
        UPDATE analytics.edge_next_research_plan_v1 p SET
          status_code=CASE
            WHEN NOT EXISTS (SELECT 1 FROM analytics.edge_next_research_plan_item_v1 i WHERE i.plan_id=p.plan_id) THEN 'EMPTY'
            WHEN EXISTS (SELECT 1 FROM analytics.edge_next_research_plan_item_v1 i WHERE i.plan_id=p.plan_id AND i.status_code='ACTIVE') THEN 'ACTIVE'
            WHEN NOT EXISTS (SELECT 1 FROM analytics.edge_next_research_plan_item_v1 i WHERE i.plan_id=p.plan_id AND i.status_code IN ('WAITING_FUTURE_DATA','ACTIVE')) THEN 'EVALUATED'
            ELSE 'WAITING_FUTURE_DATA' END,
          updated_at=clock_timestamp()
        WHERE p.status_code <> 'EMPTY'
    """)
    cursor.execute("""UPDATE analytics.edge_methodology_research_lineage_v1 l
        SET status_code=i.status_code,updated_at=clock_timestamp()
        FROM analytics.edge_next_research_plan_item_v1 i
        WHERE i.plan_item_id=l.plan_item_id AND l.status_code<>i.status_code""")


def main() -> None:
    parent_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    search_run_id = os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"]
    plan_id = uuid.uuid5(NAMESPACE, f"{parent_run_id}:{VERSION}")
    created = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            evaluated = close_evaluated(cursor, search_run_id)
            activated = activate_ready(cursor)
            cursor.execute("""
                SELECT a.*,r.strategy_code,r.parameter_grid,r.regime_policy,r.gate_policy,
                       coalesce(p.priority_rank,100) compute_priority_rank,
                       coalesce(p.coarse_budget,4) compute_budget,
                       coalesce(p.promotion_blocked,false) promotion_blocked,
                       w.result_id,w.symbol,w.parameter_json,w.fold_metrics
                FROM analytics.edge_search_algorithm_analysis_v1 a
                JOIN analytics.edge_search_algorithm_registry_v1 r USING (algorithm_code)
                LEFT JOIN analytics.edge_algorithm_compute_policy_v1 p USING (algorithm_code)
                JOIN LATERAL (
                  SELECT x.* FROM analytics.walkforward_edge_search_v3 x
                  WHERE x.search_run_id=a.search_run_id AND x.strategy_family=a.algorithm_code
                    AND x.verdict_code='OOS_FAIL'
                  ORDER BY x.folds_passed DESC,x.net_profit_factor DESC,x.net_expectancy DESC,x.result_id
                  LIMIT 1
                ) w ON true
                WHERE a.run_id=%s AND a.verdict_code='FAIL' AND r.enabled
                  AND NOT coalesce(p.promotion_blocked,false) AND coalesce(p.coarse_budget,4)>0
            """, (parent_run_id,))
            algorithm_failures = [dict(row) for row in cursor.fetchall()]
            method_failures = methodology_failures(cursor,parent_run_id)
            combined = sorted(method_failures + algorithm_failures,key=priority_score)
            failures=[]
            seen_algorithms=set()
            for row in combined:
                if row["algorithm_code"] not in seen_algorithms:
                    failures.append(row)
                    seen_algorithms.add(row["algorithm_code"])
            reason_summary = dict(Counter(row["primary_reason_code"] for row in failures))
            cursor.execute("""
                INSERT INTO analytics.edge_next_research_plan_v1
                  (plan_id,parent_run_id,parent_search_run_id,generator_version,status_code,source_failures,reason_summary)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (parent_run_id,generator_version) DO NOTHING
            """, (str(plan_id),parent_run_id,search_run_id,VERSION,
                  "WAITING_FUTURE_DATA" if failures else "EMPTY",len(failures),psycopg2.extras.Json(reason_summary)))
            for priority, row in enumerate(failures[:MAX_NEW_SCENARIOS], 1):
                adaptation, _, rationale = REASON_POLICY.get(row["primary_reason_code"],
                    ("RESEARCH_NEW_FAMILY", 9, "Сформировать новую проверяемую гипотезу."))
                source_grid = ([row["parameter_json"]] if row.get("methodology_evaluation_id") else row["parameter_grid"])
                grid = adapted_grid(source_grid, row["primary_reason_code"], row["algorithm_code"], int(row["compute_budget"]))
                fold5 = next(item for item in row["fold_metrics"] if int(item["fold"]) == 5)
                plan_item_id = uuid.uuid5(NAMESPACE, f"{plan_id}:{row['algorithm_code']}")
                scenario_id = uuid.uuid5(NAMESPACE, f"{plan_item_id}:adaptive")
                metrics = development_metrics(row["fold_metrics"]) or {}
                target_symbol = (liquid_peer(cursor,row["symbol"])
                                 if row["primary_reason_code"] in {"METHODOLOGY_CAPACITY","METHODOLOGY_PORTFOLIO_CONTRIBUTION"}
                                 else row["symbol"])
                policy = {"generator": VERSION, "plan_id": str(plan_id), "plan_item_id": str(plan_item_id),
                          "priority": priority, "adaptation_code": adaptation,
                          "gate_policy": row["gate_policy"], "selection_uses_final_holdout": False,
                          "source_symbol": row["symbol"], "target_symbol": target_symbol,
                          "methodology_evaluation_id": str(row.get("methodology_evaluation_id") or "")}
                holdout = {"selection_folds": [1, 2, 3, 4], "consumed_holdout_fold": 5,
                           "confirmation_mode": "FUTURE_DATA_ONLY", "confirmation_after": fold5["end"]}
                cursor.execute("""
                    INSERT INTO analytics.edge_search_adaptive_scenario_v1
                      (adaptive_scenario_id,parent_run_id,parent_search_run_id,parent_result_id,
                       algorithm_code,strategy_code,target_symbol,parameter_grid,selection_metrics,
                       generation_policy,holdout_policy,confirmation_after_ts,minimum_future_bars,
                       status_code,reason_code,config_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'WAITING_FUTURE_DATA','FAIL_DRIVEN_PLAN_WAITING_FUTURE_DATA',%s)
                    ON CONFLICT (parent_result_id,config_version) DO NOTHING
                """, (str(scenario_id),parent_run_id,search_run_id,str(row["result_id"]),row["algorithm_code"],
                      row["strategy_code"],target_symbol,psycopg2.extras.Json(grid),psycopg2.extras.Json(metrics),
                      psycopg2.extras.Json(policy),psycopg2.extras.Json(holdout),datetime.fromisoformat(fold5["end"]),
                      MIN_FUTURE_BARS,VERSION))
                cursor.execute("""
                    INSERT INTO analytics.edge_next_research_plan_item_v1
                      (plan_item_id,plan_id,priority,algorithm_code,strategy_code,primary_reason_code,
                       adaptation_code,parameter_grid,regime_policy,pass_gate_snapshot,pass_gate_hash,
                       evaluation_budget,source_result_id,adaptive_scenario_id,status_code,rationale_ru)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,md5(%s::jsonb::text),%s,%s,%s,
                            'WAITING_FUTURE_DATA',%s)
                    ON CONFLICT (plan_id,algorithm_code) DO NOTHING
                """, (str(plan_item_id),str(plan_id),priority,row["algorithm_code"],row["strategy_code"],
                      row["primary_reason_code"],adaptation,psycopg2.extras.Json(grid),
                      psycopg2.extras.Json(row["regime_policy"]),psycopg2.extras.Json(row["gate_policy"]),
                      json.dumps(row["gate_policy"]),len(grid),str(row["result_id"]),str(scenario_id),rationale))
                created += cursor.rowcount
                if row.get("methodology_evaluation_id"):
                    gate_code=row["primary_reason_code"].removeprefix("METHODOLOGY_")
                    cursor.execute("""INSERT INTO analytics.edge_methodology_research_lineage_v1
                      (lineage_id,evaluation_id,parent_run_id,parent_result_id,plan_id,plan_item_id,
                       adaptive_scenario_id,gate_code,adaptation_code,source_symbol,target_symbol,
                       pass_gate_snapshot,holdout_policy,status_code)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'WAITING_FUTURE_DATA')
                      ON CONFLICT(evaluation_id,gate_code) DO NOTHING""",
                      (str(uuid.uuid5(NAMESPACE,f"{row['methodology_evaluation_id']}:{gate_code}")),
                       str(row["methodology_evaluation_id"]),parent_run_id,str(row["result_id"]),
                       str(plan_id),str(plan_item_id),str(scenario_id),gate_code,adaptation,
                       row["symbol"],target_symbol,psycopg2.extras.Json(row["gate_policy"]),
                       psycopg2.extras.Json(holdout)))
            cursor.execute("""UPDATE analytics.edge_next_research_plan_v1 SET
                item_count=(SELECT count(*) FROM analytics.edge_next_research_plan_item_v1 WHERE plan_id=%s),
                total_parameter_variants=coalesce((SELECT sum(evaluation_budget) FROM analytics.edge_next_research_plan_item_v1 WHERE plan_id=%s),0),
                updated_at=clock_timestamp() WHERE plan_id=%s""", (str(plan_id),str(plan_id),str(plan_id)))
            sync_plan_statuses(cursor)
    print(f"next_research_plan_id={plan_id}")
    print(f"next_research_plan_items_created={created}")
    print(f"adaptive_scenarios_activated={activated}")
    print(f"adaptive_scenarios_evaluated={evaluated}")
    print("pass_gates=UNCHANGED")
    print("confirmation_mode=FUTURE_DATA_ONLY")
    print("VERDICT=NEXT_EDGE_RESEARCH_PLAN_READY")


if __name__ == "__main__":
    main()
