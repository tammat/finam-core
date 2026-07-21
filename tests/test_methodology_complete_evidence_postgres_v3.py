import os

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def test_active_methodology_contract_requires_complete_evidence() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT contract_code,policy
          FROM analytics.edge_methodology_contract_v1
          WHERE active
        """)
        contract_code,policy = cursor.fetchone()
        assert contract_code == "METHODOLOGY_V3_COMPLETE_EVIDENCE"
        assert float(policy["min_depth_coverage"]) == 0.80
        assert float(policy["min_exchange_timestamp_coverage"]) == 0.80
        assert int(policy["min_independent_sessions"]) == 2
        assert int(policy["min_independent_regimes"]) == 2
        assert policy["future_only_remediation_required"] is True
        assert policy["fold_overlap_forbidden"] is True


def test_walkforward_schema_persists_pre_holdout_evidence() -> None:
    with psycopg2.connect(DB) as connection, connection.cursor() as cursor:
        cursor.execute("""
          SELECT data_type
          FROM information_schema.columns
          WHERE table_schema='analytics'
            AND table_name='walkforward_variant_task_v4'
            AND column_name='pre_holdout_evidence'
        """)
        assert cursor.fetchone() == ("jsonb",)
