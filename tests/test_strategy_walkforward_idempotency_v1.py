from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_walkforward_save_is_an_idempotent_upsert() -> None:
    source = (ROOT / "src/finam_core/research/walkforward_repository.py").read_text()
    assert "UPDATE strategy_walkforward_results SET" in source
    assert "if cur.rowcount == 0:" in source
    assert "pg_advisory_xact_lock" in source
    assert "train_from, train_to, test_from, test_to" in source
    assert "computed_at = clock_timestamp()" in source


def test_existing_history_is_canonicalized_without_destructive_delete() -> None:
    sql = (ROOT / "sql/analytics/172_walkforward_result_idempotency_v1.sql").read_text()
    assert "analytics.strategy_walkforward_latest_v1" in sql
    assert "SELECT DISTINCT ON" in sql
    assert "DELETE FROM" not in sql


def test_research_verdict_reads_only_canonical_walkforward_windows() -> None:
    source = (ROOT / "src/finam_core/research/research_verdict_repository.py").read_text()
    assert "FROM analytics.strategy_walkforward_latest_v1" in source
