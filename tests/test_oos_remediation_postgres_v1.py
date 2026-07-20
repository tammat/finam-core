import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def test_latest_oos_remediation_process_is_bounded_and_auditable() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT branch_code,created_variants,pruned_variants,queued_variants,evaluated_variants,oos_pass
          FROM analytics.oos_remediation_branch_summary_v1 ORDER BY branch_code
        """)
        rows = cursor.fetchall()
        assert [row[0] for row in rows] == ["COST_REMEDIATION", "SAMPLE_EXPANSION"]
        active = {row[0]: row[3] for row in rows}
        assert active["COST_REMEDIATION"] <= 34
        assert active["SAMPLE_EXPANSION"] <= 10
        assert all(row[1] == row[2] + row[3] + row[4] for row in rows)


def test_oos_remediation_is_owned_by_db_scheduler() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT enabled,executor_code,interval_minutes
          FROM analytics.system_job_schedule_v1
          WHERE job_code='OOS_REMEDIATION_BRANCH_GENERATOR'
        """)
        enabled, executor, interval = cursor.fetchone()
        assert enabled is True
        assert executor == "OOS_REMEDIATION_BRANCH_GENERATOR_V1"
        assert interval == 15


def test_accepted_variants_keep_original_gate_policy() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT count(*)
          FROM analytics.edge_search_adaptive_scenario_v1 s
          JOIN analytics.edge_search_algorithm_registry_v1 r USING(algorithm_code)
          WHERE s.config_version LIKE 'OOS_REMEDIATION_BRANCHES_V1%%'
            AND s.generation_policy->'gate_policy' IS DISTINCT FROM r.gate_policy
        """)
        assert cursor.fetchone()[0] == 0
