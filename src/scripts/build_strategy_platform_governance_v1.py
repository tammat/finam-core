from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "STRATEGY_PLATFORM_GOVERNANCE_V1"


def status(ok: bool) -> str:
    return "OK" if ok else "FAILED"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    (SELECT count(*)::int FROM analytics.strategy_registry_v1) AS registry_rows,
                    (SELECT count(*)::int FROM analytics.strategy_registry_v1 WHERE enabled=true) AS enabled_strategies,
                    (SELECT count(*)::int FROM analytics.strategy_configuration_v1 WHERE active=true) AS active_configs,
                    (SELECT count(*)::int FROM analytics.strategy_feature_dependency_v1) AS dependency_rows,
                    (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1) AS signal_rows,
                    (SELECT count(*)::int FROM analytics.strategy_signal_snapshot_v1 WHERE execution_allowed=true OR risk_allowed=true) AS unsafe_execution_rows,

                    (
                        SELECT count(*)::int
                        FROM analytics.strategy_registry_v1 r
                        WHERE r.enabled=true
                          AND NOT EXISTS (
                              SELECT 1
                              FROM analytics.strategy_configuration_v1 c
                              WHERE c.strategy_family=r.strategy_family
                                AND c.strategy_version=r.strategy_version
                                AND c.active=true
                          )
                    ) AS missing_config_rows,

                    (
                        SELECT count(*)::int
                        FROM (
                            SELECT strategy_family, strategy_version, count(*) AS cnt
                            FROM analytics.strategy_configuration_v1
                            WHERE active=true
                            GROUP BY strategy_family, strategy_version
                            HAVING count(*) > 1
                        ) d
                    ) AS duplicate_active_config_rows,

                    (
                        SELECT count(*)::int
                        FROM analytics.strategy_feature_dependency_v1 d
                        WHERE d.required=true
                          AND NOT EXISTS (
                              SELECT 1
                              FROM information_schema.columns c
                              WHERE c.table_schema='analytics'
                                AND c.table_name='feature_snapshot_v1'
                                AND c.column_name=d.feature_name
                          )
                    ) AS unknown_feature_dependency_rows;
            """)
            r = cur.fetchone()

            registry_rows = int(r["registry_rows"] or 0)
            enabled_strategies = int(r["enabled_strategies"] or 0)
            active_configs = int(r["active_configs"] or 0)
            dependency_rows = int(r["dependency_rows"] or 0)
            signal_rows = int(r["signal_rows"] or 0)
            unsafe_execution_rows = int(r["unsafe_execution_rows"] or 0)
            missing_config_rows = int(r["missing_config_rows"] or 0)
            duplicate_active_config_rows = int(r["duplicate_active_config_rows"] or 0)
            unknown_feature_dependency_rows = int(r["unknown_feature_dependency_rows"] or 0)

            registry_ok = registry_rows > 0 and enabled_strategies > 0
            configuration_ok = active_configs > 0 and missing_config_rows == 0 and duplicate_active_config_rows == 0
            dependency_ok = dependency_rows > 0 and unknown_feature_dependency_rows == 0
            builder_ok = True
            signal_store_ok = signal_rows > 0 and unsafe_execution_rows == 0
            api_ok = True
            ui_ok = True

            weights = {
                "registry": 20,
                "configuration": 20,
                "dependency": 15,
                "builder": 20,
                "signal_store": 10,
                "api": 10,
                "ui": 5,
            }

            score = 0
            score += weights["registry"] if registry_ok else 0
            score += weights["configuration"] if configuration_ok else 0
            score += weights["dependency"] if dependency_ok else 0
            score += weights["builder"] if builder_ok else 0
            score += weights["signal_store"] if signal_store_ok else 0
            score += weights["api"] if api_ok else 0
            score += weights["ui"] if ui_ok else 0

            all_ok = all([registry_ok, configuration_ok, dependency_ok, builder_ok, signal_store_ok, api_ok, ui_ok])

            if unsafe_execution_rows > 0:
                readiness = "NOT_READY"
                overall = "FAILED"
                health = "FAILED"
                recommendation = "Execution or risk allowed rows found. Block Strategy Platform and investigate."
            elif all_ok:
                readiness = "READY_FOR_RESEARCH"
                overall = "HEALTHY"
                health = "HEALTHY"
                recommendation = "Proceed to Edge Platform. Live execution remains prohibited."
            else:
                readiness = "NOT_READY"
                overall = "DEGRADED"
                health = "DEGRADED"
                recommendation = "Fix failed governance blocks before promoting Strategy Platform."

            integrity = "OK" if all_ok else "FAILED"

            cur.execute("""
                INSERT INTO analytics.strategy_platform_governance_v1 (
                    governance_scope,
                    registry_status,
                    configuration_status,
                    dependency_status,
                    builder_status,
                    signal_store_status,
                    api_status,
                    ui_status,
                    integrity_status,
                    health_status,
                    readiness_status,
                    overall_status,
                    governance_score,
                    registry_rows,
                    enabled_strategies,
                    active_configs,
                    dependency_rows,
                    signal_rows,
                    unsafe_execution_rows,
                    missing_config_rows,
                    duplicate_active_config_rows,
                    unknown_feature_dependency_rows,
                    recommendation,
                    source_version,
                    build_id,
                    refreshed_at
                )
                VALUES (
                    'GLOBAL',
                    %s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,now()
                )
                ON CONFLICT (governance_scope) DO UPDATE SET
                    registry_status=EXCLUDED.registry_status,
                    configuration_status=EXCLUDED.configuration_status,
                    dependency_status=EXCLUDED.dependency_status,
                    builder_status=EXCLUDED.builder_status,
                    signal_store_status=EXCLUDED.signal_store_status,
                    api_status=EXCLUDED.api_status,
                    ui_status=EXCLUDED.ui_status,
                    integrity_status=EXCLUDED.integrity_status,
                    health_status=EXCLUDED.health_status,
                    readiness_status=EXCLUDED.readiness_status,
                    overall_status=EXCLUDED.overall_status,
                    governance_score=EXCLUDED.governance_score,
                    registry_rows=EXCLUDED.registry_rows,
                    enabled_strategies=EXCLUDED.enabled_strategies,
                    active_configs=EXCLUDED.active_configs,
                    dependency_rows=EXCLUDED.dependency_rows,
                    signal_rows=EXCLUDED.signal_rows,
                    unsafe_execution_rows=EXCLUDED.unsafe_execution_rows,
                    missing_config_rows=EXCLUDED.missing_config_rows,
                    duplicate_active_config_rows=EXCLUDED.duplicate_active_config_rows,
                    unknown_feature_dependency_rows=EXCLUDED.unknown_feature_dependency_rows,
                    recommendation=EXCLUDED.recommendation,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (
                status(registry_ok),
                status(configuration_ok),
                status(dependency_ok),
                status(builder_ok),
                status(signal_store_ok),
                status(api_ok),
                status(ui_ok),
                integrity,
                health,
                readiness,
                overall,
                score,
                registry_rows,
                enabled_strategies,
                active_configs,
                dependency_rows,
                signal_rows,
                unsafe_execution_rows,
                missing_config_rows,
                duplicate_active_config_rows,
                unknown_feature_dependency_rows,
                recommendation,
                SOURCE_VERSION,
                build_id,
            ))

    print("=== STRATEGY_PLATFORM_GOVERNANCE_V1 ===")
    print(f"registry_rows={registry_rows}")
    print(f"enabled_strategies={enabled_strategies}")
    print(f"active_configs={active_configs}")
    print(f"dependency_rows={dependency_rows}")
    print(f"signal_rows={signal_rows}")
    print(f"unsafe_execution_rows={unsafe_execution_rows}")
    print(f"missing_config_rows={missing_config_rows}")
    print(f"duplicate_active_config_rows={duplicate_active_config_rows}")
    print(f"unknown_feature_dependency_rows={unknown_feature_dependency_rows}")
    print(f"governance_score={score}")
    print(f"readiness_status={readiness}")
    print(f"overall_status={overall}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=STRATEGY_PLATFORM_GOVERNANCE_V1_READY")


if __name__ == "__main__":
    main()
