from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "HYPOTHESIS_FAILURE_DIAGNOSTICS_V2"
RECOMMENDATIONS = {
    "MOMENTUM": "Новый nested OOS: направление × режим × сессия; не расширять текущую сетку",
    "BREAKOUT": "Новый nested OOS: сжатие × подтверждение пробоя × сессия",
    "MEAN_REVERSION": "Новый nested OOS: режим боковика × волатильность × время возврата",
    "RELATIVE_STRENGTH": "Проверять отдельно benchmark × режим × сессия и не смешивать акции",
    "INTERMARKET_LEAD_LAG": "Проверять каждую экономическую связь отдельно; не объединять слабые пары",
}


def blockers(row: dict) -> list[str]:
    result = []
    if float(row["oos_expectancy"] or 0) <= 0:
        result.append("NEGATIVE_NET_EXPECTANCY")
    if float(row["oos_profit_factor"] or 0) < 1.10:
        result.append("PROFIT_FACTOR_BELOW_GATE")
    if int(row["oos_trades"] or 0) < 30:
        result.append("INSUFFICIENT_OOS_TRADES")
    if int(row["folds_passed"] or 0) < 2:
        result.append("TEMPORAL_INSTABILITY")
    if float(row["adjusted_p_value"] or 1) > 0.05:
        result.append("MULTIPLE_TESTING_NOT_SIGNIFICANT")
    return result or ["UNCLASSIFIED_GATE_FAILURE"]


def neighbor(a: dict, b: dict) -> bool:
    keys = set(a) | set(b)
    return sum(a.get(key) != b.get(key) for key in keys) == 1


def main() -> None:
    diagnostics_run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT execution_run_id FROM analytics.strategy_hypothesis_execution_run_v2
                ORDER BY created_at DESC LIMIT 1""")
            latest = cur.fetchone()
            if not latest:
                raise RuntimeError("NO_EXECUTION_RUN_V2")
            execution_run_id = latest["execution_run_id"]
            cur.execute("""SELECT r.*,h.hypothesis_id FROM analytics.strategy_hypothesis_execution_result_v2 r
                JOIN analytics.canonical_hypothesis_registry_v1 h USING(candidate_hash)
                WHERE r.execution_run_id=%s ORDER BY r.strategy_family,r.candidate_hash""", (execution_run_id,))
            rows = [dict(row) for row in cur.fetchall()]
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.hypothesis_failure_diagnostic_v2 (
                    diagnostics_run_id uuid NOT NULL, execution_run_id uuid NOT NULL,
                    hypothesis_id uuid NOT NULL, candidate_hash text NOT NULL,
                    strategy_family text NOT NULL, primary_failure_code text NOT NULL,
                    blocker_codes jsonb NOT NULL, neighbor_count integer NOT NULL,
                    supportive_neighbors integer NOT NULL, stability_status text NOT NULL,
                    gross_cost_attribution_status text NOT NULL,
                    recommended_action text NOT NULL, source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(diagnostics_run_id,hypothesis_id)
                );
                CREATE INDEX IF NOT EXISTS hypothesis_failure_diagnostic_latest_idx
                    ON analytics.hypothesis_failure_diagnostic_v2(created_at DESC,strategy_family,primary_failure_code);
            """)
            by_family: dict[str, list[dict]] = {}
            for row in rows:
                by_family.setdefault(row["strategy_family"], []).append(row)
            for row in rows:
                family_rows = by_family[row["strategy_family"]]
                adjacent = [other for other in family_rows if other["candidate_hash"] != row["candidate_hash"]
                            and neighbor(row["parameter_json"], other["parameter_json"])]
                supportive = [other for other in adjacent if float(other["oos_profit_factor"] or 0) >= 1.0
                              and float(other["oos_expectancy"] or 0) > 0]
                codes = blockers(row)
                stability = "SUPPORTED" if len(supportive) >= 2 else "NOT_SUPPORTED"
                cur.execute("""INSERT INTO analytics.hypothesis_failure_diagnostic_v2
                    (diagnostics_run_id,execution_run_id,hypothesis_id,candidate_hash,strategy_family,
                     primary_failure_code,blocker_codes,neighbor_count,supportive_neighbors,stability_status,
                     gross_cost_attribution_status,recommended_action,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'UNAVAILABLE_NO_GROSS_METRIC',%s,%s)""",
                    (diagnostics_run_id,execution_run_id,row["hypothesis_id"],row["candidate_hash"],row["strategy_family"],
                     codes[0],psycopg2.extras.Json(codes),len(adjacent),len(supportive),stability,
                     RECOMMENDATIONS[row["strategy_family"]],SOURCE_VERSION))

    print(f"diagnostics_run_id={diagnostics_run_id}")
    print(f"execution_run_id={execution_run_id}")
    print(f"diagnosed={len(rows)}")
    print("verdicts_changed=0")
    print("paper_created=0")
    print("live_allowed=0")
    print("VERDICT=HYPOTHESIS_FAILURE_DIAGNOSTICS_V2_OK")


if __name__ == "__main__":
    main()
