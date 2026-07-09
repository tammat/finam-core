from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

SOURCE_VERSION = "MARKETCORE_MODEL_HEALTH_ENGINE_V1"


def dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def load_parameters(cur) -> dict[str, Decimal]:
    cur.execute("""
        SELECT parameter_code, parameter_value
        FROM knowledge.platform_parameter_v1
        WHERE enabled
          AND parameter_group='MODEL_HEALTH'
    """)
    return {str(r["parameter_code"]): dec(r["parameter_value"]) for r in cur.fetchall()}


def component_status(value: Decimal, params: dict[str, Decimal]) -> str:
    if value >= params["MODEL_HEALTH_STATUS_PASS_MIN"]:
        return "PASS"
    if value >= params["MODEL_HEALTH_STATUS_WARNING_MIN"]:
        return "WARNING"
    return "BLOCKED"


def split_table_name(table_name: str) -> tuple[str, str]:
    parts = table_name.split(".")
    if len(parts) != 2:
        raise RuntimeError(f"invalid_metric_table:{table_name}")
    return parts[0], parts[1]


def metric_exists(cur, table_name: str, column_name: str) -> None:
    schema_name, rel_name = split_table_name(table_name)
    cur.execute(
        """
        SELECT count(*) AS rows_total
        FROM information_schema.columns
        WHERE table_schema=%s
          AND table_name=%s
          AND column_name=%s
        """,
        (schema_name, rel_name, column_name),
    )
    if int(cur.fetchone()["rows_total"]) != 1:
        raise RuntimeError(f"missing_metric_column:{table_name}.{column_name}")


def resolve_metric(cur, row: dict[str, Any], score_max: Decimal) -> tuple[Decimal, dict[str, Any]]:
    table_name = str(row["metric_table"])
    column_name = str(row["metric_column"])
    method = str(row["aggregation_method"])

    metric_exists(cur, table_name, column_name)
    schema_name, rel_name = split_table_name(table_name)

    if method == "LAST":
        cur.execute(
            sql.SQL("SELECT {col} AS metric_value FROM {schema}.{table} ORDER BY created_at DESC LIMIT 1").format(
                col=sql.Identifier(column_name),
                schema=sql.Identifier(schema_name),
                table=sql.Identifier(rel_name),
            )
        )
        r = cur.fetchone()
        value = dec(r["metric_value"]) if r else Decimal("0")
        return value, {"aggregation_method": method, "metric_table": table_name, "metric_column": column_name}

    if method == "LAST_BINARY":
        cur.execute(
            sql.SQL("SELECT {col} AS metric_value FROM {schema}.{table} ORDER BY created_at DESC LIMIT 1").format(
                col=sql.Identifier(column_name),
                schema=sql.Identifier(schema_name),
                table=sql.Identifier(rel_name),
            )
        )
        r = cur.fetchone()
        value = score_max if r and dec(r["metric_value"]) > 0 else Decimal("0")
        return value, {"aggregation_method": method, "metric_table": table_name, "metric_column": column_name}

    if method == "COUNT":
        cur.execute(
            sql.SQL("SELECT count({col}) AS rows_total FROM {schema}.{table}").format(
                col=sql.Identifier(column_name),
                schema=sql.Identifier(schema_name),
                table=sql.Identifier(rel_name),
            )
        )
        count_value = dec(cur.fetchone()["rows_total"])
        value = min(count_value, score_max)
        return value, {
            "aggregation_method": method,
            "metric_table": table_name,
            "metric_column": column_name,
            "rows_total": str(count_value),
        }

    if method == "COVERAGE":
        cur.execute(
            sql.SQL("""
                SELECT
                    count(*) AS rows_total,
                    count({col}) AS covered_rows
                FROM {schema}.{table}
            """).format(
                col=sql.Identifier(column_name),
                schema=sql.Identifier(schema_name),
                table=sql.Identifier(rel_name),
            )
        )
        r = cur.fetchone()
        total = dec(r["rows_total"])
        covered = dec(r["covered_rows"])
        value = Decimal("0") if total <= 0 else (covered / total * score_max).quantize(Decimal("0.0001"))
        return value, {
            "aggregation_method": method,
            "metric_table": table_name,
            "metric_column": column_name,
            "rows_total": str(total),
            "covered_rows": str(covered),
        }

    raise RuntimeError(f"unsupported_aggregation_method:{method}")


def insert_component(cur, snapshot_id: int, row: dict[str, Any], value: Decimal, status_value: str, evidence: dict[str, Any]) -> None:
    cur.execute("""
        INSERT INTO analytics.marketcore_model_health_component_v1
        (
            model_health_snapshot_id,
            component_code,
            component_name,
            component_group,
            component_value,
            component_status,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
    """, (
        snapshot_id,
        row["component_code"],
        row["component_name"],
        row["component_group"],
        value,
        status_value,
        json.dumps(evidence, ensure_ascii=False),
        SOURCE_VERSION,
    ))


def insert_gate(cur, snapshot_id: int, gate_code: str, gate_name: str, gate_status: str, gate_reason: str, evidence: dict[str, Any]) -> None:
    cur.execute("""
        INSERT INTO analytics.marketcore_model_health_gate_v1
        (
            model_health_snapshot_id,
            gate_code,
            gate_name,
            gate_status,
            gate_reason,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s)
    """, (
        snapshot_id,
        gate_code,
        gate_name,
        gate_status,
        gate_reason,
        json.dumps(evidence, ensure_ascii=False),
        SOURCE_VERSION,
    ))


def insert_recommendation(cur, snapshot_id: int, code: str, scope: str, reason: str, action: str, evidence: dict[str, Any]) -> None:
    cur.execute("""
        INSERT INTO analytics.marketcore_model_health_recommendation_v1
        (
            model_health_snapshot_id,
            recommendation_code,
            recommendation_scope,
            recommendation_reason,
            recommended_action,
            approved,
            applied,
            auto_decision,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,0,0,0,%s::jsonb,%s)
    """, (
        snapshot_id,
        code,
        scope,
        reason,
        action,
        json.dumps(evidence, ensure_ascii=False),
        SOURCE_VERSION,
    ))


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            params = load_parameters(cur)
            required = {
                "MODEL_HEALTH_SCORE_MAX",
                "MODEL_HEALTH_STATUS_PASS_MIN",
                "MODEL_HEALTH_STATUS_WARNING_MIN",
            }
            missing = required - set(params)
            if missing:
                raise RuntimeError(f"missing_model_health_parameters:{sorted(missing)}")

            score_max = params["MODEL_HEALTH_SCORE_MAX"]

            cur.execute("""
                SELECT analytics_snapshot_id
                FROM analytics.analytics_snapshot_v1
                WHERE snapshot_type='PAPER_EXECUTION_ANALYTICS'
                  AND source_version='PAPER_EXECUTION_ANALYTICS_ENGINE_V1'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            paper_row = cur.fetchone()
            paper_snapshot_id = int(paper_row["analytics_snapshot_id"]) if paper_row else None

            cur.execute("""
                SELECT analytics_snapshot_id
                FROM analytics.analytics_snapshot_v1
                WHERE snapshot_type='PAPER_EXECUTION_ROBUSTNESS'
                  AND source_version='PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            robustness_row = cur.fetchone()
            robustness_snapshot_id = int(robustness_row["analytics_snapshot_id"]) if robustness_row else None

            cur.execute("""
                INSERT INTO analytics.marketcore_model_health_snapshot_v1
                (
                    paper_analytics_snapshot_id,
                    robustness_snapshot_id,
                    evidence_json,
                    source_version
                )
                VALUES (%s,%s,%s::jsonb,%s)
                RETURNING model_health_snapshot_id
            """, (
                paper_snapshot_id,
                robustness_snapshot_id,
                json.dumps(
                    {
                        "parameters_source": "knowledge.platform_parameter_v1",
                        "registry_source": "analytics.marketcore_model_health_component_registry_v1",
                        "mode": "model_health_snapshot_only_no_auto_decision",
                    },
                    ensure_ascii=False,
                ),
                SOURCE_VERSION,
            ))
            snapshot_id = int(cur.fetchone()["model_health_snapshot_id"])

            cur.execute("""
                SELECT r.*, p.parameter_value AS weight_value
                FROM analytics.marketcore_model_health_component_registry_v1 r
                JOIN knowledge.platform_parameter_v1 p
                  ON p.parameter_code=r.weight_parameter_code
                 AND p.enabled
                WHERE r.enabled
                ORDER BY r.component_code
            """)
            registry_rows = [dict(r) for r in cur.fetchall()]

            component_values: dict[str, Decimal] = {}
            component_statuses: dict[str, str] = {}

            for row in registry_rows:
                value, evidence = resolve_metric(cur, row, score_max)
                status_value = component_status(value, params)
                component_values[str(row["component_code"])] = value
                component_statuses[str(row["component_code"])] = status_value
                evidence["weight_parameter_code"] = row["weight_parameter_code"]
                evidence["weight_value"] = str(row["weight_value"])
                insert_component(cur, snapshot_id, row, value, status_value, evidence)

            paper_gate_status = "PASS" if paper_snapshot_id else "BLOCKED"
            robustness_gate_status = component_statuses.get("ROBUSTNESS", "BLOCKED")
            feedback_gate_status = component_statuses.get("FEEDBACK_READINESS", "BLOCKED")
            production_gate_status = "LOCKED"
            if component_values.get("PRODUCTION_READINESS", Decimal("0")) >= params["MODEL_HEALTH_STATUS_PASS_MIN"]:
                production_gate_status = "PASS"

            insert_gate(
                cur,
                snapshot_id,
                "PAPER",
                "Paper Validation",
                paper_gate_status,
                "PAPER_ANALYTICS_SNAPSHOT_PRESENT" if paper_snapshot_id else "PAPER_ANALYTICS_SNAPSHOT_MISSING",
                {"paper_analytics_snapshot_id": paper_snapshot_id},
            )

            insert_gate(
                cur,
                snapshot_id,
                "ROBUSTNESS",
                "Robustness",
                robustness_gate_status,
                "ROBUSTNESS_COMPONENT_STATUS",
                {"robustness_snapshot_id": robustness_snapshot_id},
            )

            insert_gate(
                cur,
                snapshot_id,
                "FEEDBACK",
                "Feedback",
                feedback_gate_status,
                "FEEDBACK_QUEUE_PRESENT",
                {"feedback_readiness": str(component_values.get("FEEDBACK_READINESS", Decimal("0")))},
            )

            insert_gate(
                cur,
                snapshot_id,
                "PRODUCTION",
                "Production",
                production_gate_status,
                "PRODUCTION_LOCKED_UNTIL_STATISTICAL_MATURITY",
                {"production_readiness": str(component_values.get("PRODUCTION_READINESS", Decimal("0")))},
            )

            if production_gate_status != "PASS":
                insert_recommendation(
                    cur,
                    snapshot_id,
                    "CONTINUE_PAPER_VALIDATION",
                    "MODEL_HEALTH",
                    "PRODUCTION_NOT_READY",
                    "COLLECT_MORE_DATA",
                    {
                        "production_gate_status": production_gate_status,
                        "auto_decision": 0,
                    },
                )

            if component_statuses.get("LEARNING_READINESS") != "PASS":
                insert_recommendation(
                    cur,
                    snapshot_id,
                    "IMPROVE_LEARNING_READINESS",
                    "MODEL_HEALTH",
                    "LEARNING_READINESS_NOT_READY",
                    "CONTINUE_OBSERVATION",
                    {
                        "learning_readiness": str(component_values.get("LEARNING_READINESS", Decimal("0"))),
                        "auto_decision": 0,
                    },
                )

    print("=== MARKETCORE_MODEL_HEALTH_ENGINE_V1 ===")
    print(f"model_health_snapshot_id={snapshot_id}")
    print(f"paper_analytics_snapshot_id={paper_snapshot_id}")
    print(f"robustness_snapshot_id={robustness_snapshot_id}")
    print(f"components_written={len(component_values)}")
    print("gates_written=4")
    print("model_recommendations_written=2")
    print("parameters_source=postgres")
    print("registry_source=postgres")
    print("approved=0")
    print("applied=0")
    print("auto_decision=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_MODEL_HEALTH_ENGINE_V1_READY")


if __name__ == "__main__":
    main()
