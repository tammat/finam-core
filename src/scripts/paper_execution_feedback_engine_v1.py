from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "PAPER_EXECUTION_FEEDBACK_ENGINE_V1"


def dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def load_parameters(cur) -> dict[str, str]:
    cur.execute("""
        SELECT parameter_code, parameter_value
        FROM knowledge.platform_parameter_v1
        WHERE enabled
    """)
    return {str(r["parameter_code"]): str(r["parameter_value"]) for r in cur.fetchall()}


def rule_matches(value: Any, operator_code: str, threshold: str) -> bool:
    if operator_code == "LT":
        return dec(value) < dec(threshold)
    if operator_code == "GT":
        return dec(value) > dec(threshold)
    if operator_code == "EQ":
        return str(value) == str(threshold)
    return False


def insert_feedback(
    cur,
    analytics_snapshot_id: int,
    robustness_snapshot_id: int,
    scope_code: str,
    target: str,
    reason: dict[str, Any],
    sample_status: str,
    confidence: Decimal,
    evidence: dict[str, Any],
) -> None:
    cur.execute("""
        INSERT INTO analytics.paper_execution_feedback_v1
        (
            analytics_snapshot_id,
            robustness_snapshot_id,
            feedback_scope_code,
            feedback_target,
            feedback_reason,
            feedback_reason_code,
            severity,
            feedback_severity_code,
            confidence,
            recommended_action_code,
            sample_status,
            approved,
            applied,
            auto_decision,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,0,%s::jsonb,%s)
    """, (
        analytics_snapshot_id,
        robustness_snapshot_id,
        scope_code,
        target,
        reason["reason_code"],
        reason["reason_code"],
        reason["default_severity_code"],
        reason["default_severity_code"],
        confidence,
        reason["default_action_code"],
        sample_status,
        json.dumps(evidence, ensure_ascii=False),
        SOURCE_VERSION,
    ))


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            parameters = load_parameters(cur)

            cur.execute("""
                SELECT analytics_snapshot_id
                FROM analytics.analytics_snapshot_v1
                WHERE snapshot_type='PAPER_EXECUTION_ANALYTICS'
                  AND source_version='PAPER_EXECUTION_ANALYTICS_ENGINE_V1'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            analytics_snapshot_id = int(cur.fetchone()["analytics_snapshot_id"])

            cur.execute("""
                SELECT *
                FROM analytics.paper_execution_robustness_audit_v1
                WHERE source_version='PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'
                ORDER BY created_at DESC
                LIMIT 1
            """)
            robustness = dict(cur.fetchone())
            robustness_snapshot_id = int(robustness["analytics_snapshot_id"])

            cur.execute("""
                SELECT r.*, d.default_action_code, d.default_severity_code
                FROM analytics.paper_execution_feedback_rule_v1 r
                JOIN analytics.paper_execution_feedback_reason_v1 d
                  ON d.reason_code=r.reason_code
                 AND d.enabled
                WHERE r.enabled
                ORDER BY r.feedback_rule_code
            """)
            rules = [dict(r) for r in cur.fetchall()]

            created = 0

            for rule in rules:
                threshold = parameters.get(str(rule["threshold_parameter_code"]))
                if threshold is None:
                    continue

                metric_source = str(rule["metric_source"])
                metric_code = str(rule["metric_code"])

                if metric_source == "ROBUSTNESS":
                    value = robustness.get(metric_code)
                    if rule_matches(value, str(rule["operator_code"]), threshold):
                        insert_feedback(
                            cur,
                            analytics_snapshot_id,
                            robustness_snapshot_id,
                            str(rule["feedback_scope_code"]),
                            "SYSTEM",
                            rule,
                            str(robustness["sample_status"]),
                            Decimal("1"),
                            {
                                "rule_code": rule["feedback_rule_code"],
                                "metric_source": metric_source,
                                "metric_code": metric_code,
                                "metric_value": str(value),
                                "threshold": threshold,
                                "mode": "recommendation_only_no_auto_decision",
                            },
                        )
                        created += 1

                elif metric_source == "PROFILE":
                    cur.execute("""
                        SELECT *
                        FROM analytics.paper_execution_profile_scorecard_v1
                        WHERE analytics_snapshot_id=%s
                    """, (analytics_snapshot_id,))
                    for row in cur.fetchall():
                        value = row[metric_code]
                        if rule_matches(value, str(rule["operator_code"]), threshold):
                            insert_feedback(
                                cur, analytics_snapshot_id, robustness_snapshot_id,
                                str(rule["feedback_scope_code"]),
                                str(row["profile_code"]),
                                rule,
                                str(row["sample_status"]),
                                Decimal("1"),
                                {"rule_code": rule["feedback_rule_code"], "metric_value": str(value)}
                            )
                            created += 1

                elif metric_source == "SOURCE":
                    cur.execute("""
                        SELECT *
                        FROM analytics.paper_execution_source_scorecard_v1
                        WHERE analytics_snapshot_id=%s
                    """, (analytics_snapshot_id,))
                    for row in cur.fetchall():
                        value = row[metric_code]
                        if rule_matches(value, str(rule["operator_code"]), threshold):
                            target = "|".join([
                                str(row["entry_source"]),
                                str(row["stop_source"]),
                                str(row["target_source"]),
                            ])
                            insert_feedback(
                                cur, analytics_snapshot_id, robustness_snapshot_id,
                                str(rule["feedback_scope_code"]),
                                target,
                                rule,
                                str(row["sample_status"]),
                                Decimal("1"),
                                {"rule_code": rule["feedback_rule_code"], "metric_value": str(value)}
                            )
                            created += 1

                elif metric_source == "REGIME":
                    cur.execute("""
                        SELECT *
                        FROM analytics.paper_execution_regime_scorecard_v1
                        WHERE analytics_snapshot_id=%s
                    """, (analytics_snapshot_id,))
                    for row in cur.fetchall():
                        value = row[metric_code]
                        if rule_matches(value, str(rule["operator_code"]), threshold):
                            insert_feedback(
                                cur, analytics_snapshot_id, robustness_snapshot_id,
                                str(rule["feedback_scope_code"]),
                                str(row["regime_code"]),
                                rule,
                                str(row["sample_status"]),
                                Decimal("1"),
                                {"rule_code": rule["feedback_rule_code"], "metric_value": str(value)}
                            )
                            created += 1

    print("=== PAPER_EXECUTION_FEEDBACK_ENGINE_V1 ===")
    print(f"analytics_snapshot_id={analytics_snapshot_id}")
    print(f"robustness_snapshot_id={robustness_snapshot_id}")
    print(f"feedback_rows_created={created}")
    print("mode=recommendation_only")
    print("approved=0")
    print("applied=0")
    print("auto_decision=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EXECUTION_FEEDBACK_ENGINE_V1_READY")


if __name__ == "__main__":
    main()
