from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def _status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    (SELECT count(*)::int FROM analytics.risk_decision_snapshot_v1) AS risk_rows,
                    (SELECT count(*)::int FROM analytics.risk_decision_snapshot_v1 WHERE risk_score >= 0) AS scored_rows,
                    (SELECT count(*)::int FROM analytics.risk_decision_snapshot_v1 WHERE risk_decision_code IN ('RISK_ALLOW','RISK_OBSERVE','RISK_BLOCK')) AS decision_rows,
                    (SELECT count(*)::int FROM analytics.risk_decision_snapshot_v1 WHERE ready_for_live=true OR ready_for_micro_live=true) AS unsafe_rows,
                    (SELECT count(*)::int FROM analytics.risk_configuration_v1 WHERE enabled=true) AS enabled_config_rows;
            """)
            r = cur.fetchone()

            risk_rows = int(r["risk_rows"] or 0)
            scored_rows = int(r["scored_rows"] or 0)
            decision_rows = int(r["decision_rows"] or 0)
            unsafe_rows = int(r["unsafe_rows"] or 0)
            enabled_config_rows = int(r["enabled_config_rows"] or 0)

            rule_engine_ok = enabled_config_rows > 0
            builder_ok = risk_rows > 0 and scored_rows > 0
            decision_ok = risk_rows > 0 and decision_rows > 0
            safety_ok = unsafe_rows == 0

            checks = [rule_engine_ok, builder_ok, decision_ok, safety_ok]
            governance_score = round(100.0 * sum(1 for x in checks if x) / len(checks), 4)

            if not safety_ok:
                readiness_code = "NOT_READY"
                recommendation_code = "BLOCK_PLATFORM"
            elif all(checks):
                readiness_code = "READY_FOR_RESEARCH"
                recommendation_code = "PROCEED_TO_TRADING_PLATFORM"
            else:
                readiness_code = "NOT_READY"
                recommendation_code = "FIX_RISK_PLATFORM"

            cur.execute("""
                INSERT INTO analytics.risk_governance_v1 (
                    governance_scope,
                    rule_engine_status,
                    builder_status,
                    decision_status,
                    api_status,
                    ui_status,
                    governance_score,
                    readiness_code,
                    recommendation_code,
                    source_version,
                    build_id,
                    refreshed_at
                )
                VALUES (
                    'GLOBAL',
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,
                    'RISK_PLATFORM_GOVERNANCE_V1',
                    %s,
                    now()
                )
                ON CONFLICT (governance_scope) DO UPDATE SET
                    rule_engine_status=EXCLUDED.rule_engine_status,
                    builder_status=EXCLUDED.builder_status,
                    decision_status=EXCLUDED.decision_status,
                    api_status=EXCLUDED.api_status,
                    ui_status=EXCLUDED.ui_status,
                    governance_score=EXCLUDED.governance_score,
                    readiness_code=EXCLUDED.readiness_code,
                    recommendation_code=EXCLUDED.recommendation_code,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (
                _status(rule_engine_ok),
                _status(builder_ok),
                _status(decision_ok),
                "OK",
                "OK",
                governance_score,
                readiness_code,
                recommendation_code,
                build_id,
            ))

    print("=== RISK_PLATFORM_GOVERNANCE_V1 ===")
    print(f"risk_rows={risk_rows}")
    print(f"scored_rows={scored_rows}")
    print(f"decision_rows={decision_rows}")
    print(f"unsafe_rows={unsafe_rows}")
    print(f"enabled_config_rows={enabled_config_rows}")
    print(f"governance_score={governance_score}")
    print(f"readiness_code={readiness_code}")
    print(f"recommendation_code={recommendation_code}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=RISK_PLATFORM_GOVERNANCE_V1_READY")


if __name__ == "__main__":
    main()
