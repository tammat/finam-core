from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "sql/analytics/224_disable_unallowed_legacy_jobs_v1.sql"


def test_only_named_unallowed_legacy_jobs_are_disabled() -> None:
    sql = MIGRATION.read_text()
    assert "SET enabled=false" in sql
    for code in (
        "ARCHIVE_EXACT_V3_BRANCH_PLAN", "ARCHIVE_V3_OOS_BRIDGE",
        "INSTRUMENT_DATA_REMEDIATION", "TEMPORAL_OOS_BRANCH_GENERATOR",
        "TRADE_OUTCOME_HYPOTHESIS_GENERATOR", "TRADE_OUTCOME_OOS_ADMISSION",
        "TRADE_OUTCOME_PATTERN_ANALYSIS",
    ):
        assert f"'{code}'" in sql
    assert "DISABLED_LEGACY_EXECUTOR_NOT_ALLOWED_V1" in sql
    assert "executor_code IN" in sql
