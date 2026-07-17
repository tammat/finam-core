from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

EXPLANATIONS = {
    "INSUFFICIENT_TRADES": "Недостаточно сделок для статистически надёжного решения.",
    "NEGATIVE_COST_ADJUSTED_EXPECTANCY": "После комиссий и проскальзывания математическое ожидание отрицательное.",
    "PROFIT_FACTOR_BELOW_GATE": "Profit Factor не достиг установленного в БД порога.",
    "WALKFORWARD_FOLDS_UNSTABLE": "Результат нестабилен между временными фолдами.",
    "FINAL_HOLDOUT_FAILED": "Независимый финальный holdout не подтвердил результат.",
    "WALKFORWARD_COST_ADJUSTED_PASS": "Алгоритм прошёл все критерии с учётом торговых издержек.",
}
RECOMMENDATIONS = {
    "INSUFFICIENT_TRADES": "EXPAND_CLEAN_SAMPLE",
    "NEGATIVE_COST_ADJUSTED_EXPECTANCY": "REVIEW_SIGNAL_AND_COST_MODEL",
    "PROFIT_FACTOR_BELOW_GATE": "SEARCH_NEW_PARAMETERS_WITHOUT_WEAKENING_GATE",
    "WALKFORWARD_FOLDS_UNSTABLE": "REFINE_REGIME_CONTRACT",
    "FINAL_HOLDOUT_FAILED": "REJECT_AND_PRESERVE_HOLDOUT",
    "WALKFORWARD_COST_ADJUSTED_PASS": "PROMOTE_CONFIRMED_PASS",
}


def main() -> int:
    scenario_run_id = uuid.UUID(os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"])
    search_run_id = uuid.UUID(os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"])
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                WITH grouped AS (
                  SELECT strategy_family algorithm_code,count(*) candidates_evaluated,
                         count(*) FILTER (WHERE verdict_code='OOS_PASS') passes,
                         max(net_profit_factor) best_pf,max(net_expectancy) best_expectancy,
                         max(folds_passed) best_folds,max(total_trades) max_trades
                  FROM analytics.walkforward_edge_search_v3 WHERE search_run_id=%s
                  GROUP BY strategy_family
                ), reasons AS (
                  SELECT strategy_family algorithm_code,
                         jsonb_object_agg(reason_code,amount) reason_distribution
                  FROM (SELECT strategy_family,reason_code,count(*) amount
                        FROM analytics.walkforward_edge_search_v3 WHERE search_run_id=%s
                        GROUP BY strategy_family,reason_code) x GROUP BY strategy_family
                )
                SELECT g.*,r.reason_distribution,
                       CASE WHEN g.passes>0 THEN 'WALKFORWARD_COST_ADJUSTED_PASS'
                            ELSE (SELECT reason_code FROM analytics.walkforward_edge_search_v3 w
                                  WHERE w.search_run_id=%s AND w.strategy_family=g.algorithm_code
                                  GROUP BY reason_code ORDER BY count(*) DESC,reason_code LIMIT 1) END primary_reason
                FROM grouped g JOIN reasons r USING(algorithm_code) ORDER BY algorithm_code
            """, (str(search_run_id),str(search_run_id),str(search_run_id)))
            rows = cursor.fetchall()
            for row in rows:
                reason = str(row["primary_reason"])
                passed = int(row["passes"] or 0)
                best_metrics = {"profit_factor":float(row["best_pf"] or 0),
                                "expectancy":float(row["best_expectancy"] or 0),
                                "folds":int(row["best_folds"] or 0),
                                "trades":int(row["max_trades"] or 0)}
                cursor.execute("""
                    INSERT INTO analytics.edge_search_algorithm_analysis_v1
                      (run_id,search_run_id,algorithm_code,verdict_code,candidates_evaluated,passes,
                       primary_reason_code,reason_distribution,best_metrics,success_factors,failure_factors,
                       recommendation_code,explanation_ru)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s)
                    ON CONFLICT (run_id,algorithm_code) DO UPDATE SET
                      verdict_code=EXCLUDED.verdict_code,candidates_evaluated=EXCLUDED.candidates_evaluated,
                      passes=EXCLUDED.passes,primary_reason_code=EXCLUDED.primary_reason_code,
                      reason_distribution=EXCLUDED.reason_distribution,best_metrics=EXCLUDED.best_metrics,
                      success_factors=EXCLUDED.success_factors,failure_factors=EXCLUDED.failure_factors,
                      recommendation_code=EXCLUDED.recommendation_code,explanation_ru=EXCLUDED.explanation_ru
                """, (str(scenario_run_id),str(search_run_id),row["algorithm_code"],"PASS" if passed else "FAIL",
                      row["candidates_evaluated"],passed,reason,json.dumps(row["reason_distribution"]),
                      json.dumps(best_metrics),json.dumps(["STRICT_OOS_PASS"] if passed else []),
                      json.dumps([] if passed else [reason]),RECOMMENDATIONS.get(reason,"REVIEW_AUDIT_EVIDENCE"),
                      EXPLANATIONS.get(reason,"Причина сохранена; требуется анализ подтверждённых метрик.")))
    print(f"scenario_run_id={scenario_run_id}")
    print(f"search_run_id={search_run_id}")
    print(f"algorithms_analyzed={len(rows)}")
    print("VERDICT=EDGE_SEARCH_RESULTS_ANALYZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
