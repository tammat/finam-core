from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
NAMESPACE = uuid.UUID("f0f90ceb-f48d-4ed0-b6f1-c97913051420")


def _positive_session(evidence: dict) -> bool:
    return any(
        int(item.get("trades", 0)) >= 5
        and float(item.get("net_expectancy", 0)) > 0
        and float(item.get("net_profit_factor", 0)) > 1
        for item in (evidence.get("session_breakdown") or {}).values()
    )


def _non_fixed_exit(evidence: dict) -> bool:
    return any(code != "FIXED_HOLD" and int(amount or 0) > 0
               for code, amount in (evidence.get("exit_reason_breakdown") or {}).items())


def _drawdown_allowed(row: dict) -> bool:
    execution = row["evidence"].get("execution_policy") or row["parameter_json"].get("execution_policy") or {}
    equity = float(execution.get("research_equity_rub", 100000))
    limit = equity * float(execution.get("max_gross_leverage", 3.0))
    return float(row.get("max_drawdown") or 0) >= -limit


def _stages(rows: list[dict], code: str) -> list[tuple[str, int]]:
    current = rows
    result = [("INPUT", len(current))]
    predicates = {
        "ENTRY": (
            ("CONTRACT", lambda r: r["parameter_json"].get("entry_policy_code") == "META_ENTRY_V2"),
            ("TRADES", lambda r: int(r.get("total_trades") or 0) > 0),
            ("GROSS_EDGE", lambda r: bool(r.get("in_sample_passed"))),
        ),
        "EXIT": (
            ("DYNAMIC", lambda r: r["parameter_json"].get("exit_policy_code") == "DYNAMIC_EXIT_V1"),
            ("RISK_EXIT", lambda r: _non_fixed_exit(r["evidence"])),
            ("STABLE", lambda r: bool(r.get("stability_passed"))),
        ),
        "SESSION": (
            ("COVERED", lambda r: bool(r["evidence"].get("session_breakdown"))),
            ("POSITIVE", lambda r: _positive_session(r["evidence"])),
            ("STABLE", lambda r: bool(r.get("stability_passed"))),
        ),
        "EXECUTION": (
            ("SPEC", lambda r: float(r["evidence"].get("contract_spec_coverage", 0)) >= 1),
            ("FILL", lambda r: float(r["evidence"].get("average_fill_ratio", 0)) >= float((r["evidence"].get("execution_policy") or {}).get("minimum_fill_ratio", .25))),
            ("STRESS", lambda r: bool(r.get("execution_pass"))),
        ),
        "RISK": (
            ("DRAWDOWN", _drawdown_allowed),
            ("STRESS", lambda r: float(r["evidence"].get("stressed_expectancy", 0)) > 0),
            ("CAPACITY", lambda r: bool(r.get("capacity_pass"))),
        ),
        "PORTFOLIO": (
            ("CAPACITY", lambda r: bool(r.get("capacity_pass"))),
            ("OVERLAP", lambda r: bool(r["evidence"].get("empty_portfolio")) or int(r["evidence"].get("portfolio_overlap_days", 0)) >= int((r["evidence"].get("contract_policy") or {}).get("min_portfolio_overlap_days", 20))),
            ("CONTRIBUTION", lambda r: bool(r.get("portfolio_pass"))),
        ),
    }[code]
    for stage_code, predicate in predicates:
        current = [row for row in current if predicate(row)]
        result.append((stage_code, len(current)))
    return result


def main() -> int:
    scenario_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    search_run_id = os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"]
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT w.result_id,w.parameter_json,w.total_trades,w.max_drawdown,
                    w.in_sample_passed,w.stability_passed,e.execution_pass,e.capacity_pass,
                    e.portfolio_pass,e.evidence
                FROM analytics.walkforward_edge_search_v3 w
                JOIN analytics.edge_methodology_evaluation_v1 e
                  ON e.search_run_id=w.search_run_id AND e.result_id=w.result_id
                WHERE w.search_run_id=%s AND e.scenario_run_id=%s""", (search_run_id, scenario_run_id))
            rows = [dict(row) for row in cursor.fetchall()]
            if not rows:
                raise RuntimeError("DIAGNOSTIC_FUNNEL_EVIDENCE_MISSING")
            cursor.execute("SELECT funnel_code,recommendation_code FROM analytics.edge_diagnostic_funnel_definition_v1 WHERE enabled ORDER BY display_order")
            definitions = cursor.fetchall()
            for definition in definitions:
                code = str(definition["funnel_code"])
                stages = _stages(rows, code)
                losses = [(stages[index - 1][1] - count, stage) for index, (stage, count) in enumerate(stages) if index]
                lost, bottleneck = max(losses, key=lambda item: item[0])
                final_count = stages[-1][1]
                status = "PASS" if final_count else "BLOCKED"
                funnel_run_id = uuid.uuid5(NAMESPACE, f"{search_run_id}:{code}")
                cursor.execute("""INSERT INTO analytics.edge_diagnostic_funnel_run_v1
                    (funnel_run_id,scenario_run_id,search_run_id,funnel_code,input_count,final_count,
                     lost_count,bottleneck_stage,recommendation_code,status_code)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(search_run_id,funnel_code) DO UPDATE SET
                      scenario_run_id=EXCLUDED.scenario_run_id,input_count=EXCLUDED.input_count,
                      final_count=EXCLUDED.final_count,lost_count=EXCLUDED.lost_count,
                      bottleneck_stage=EXCLUDED.bottleneck_stage,recommendation_code=EXCLUDED.recommendation_code,
                      status_code=EXCLUDED.status_code,created_at=clock_timestamp()""",
                    (str(funnel_run_id), scenario_run_id, search_run_id, code, stages[0][1], final_count,
                     lost, bottleneck, definition["recommendation_code"], status))
                cursor.execute("DELETE FROM analytics.edge_diagnostic_funnel_stage_v1 WHERE funnel_run_id=%s", (str(funnel_run_id),))
                previous = stages[0][1]
                for order, (stage, count) in enumerate(stages, start=1):
                    cursor.execute("""INSERT INTO analytics.edge_diagnostic_funnel_stage_v1
                        (funnel_run_id,stage_order,stage_code,evaluated_count,passed_count,lost_count)
                        VALUES(%s,%s,%s,%s,%s,%s)""",
                        (str(funnel_run_id), order, stage, previous, count, max(previous-count, 0)))
                    previous = count
    print(f"diagnostic_funnels={len(definitions)}")
    print(f"diagnostic_variants={len(rows)}")
    print("promotion_gates_changed=0")
    print("VERDICT=EDGE_DIAGNOSTIC_FUNNELS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
