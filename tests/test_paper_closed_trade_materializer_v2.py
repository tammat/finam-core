from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_materializer_writes_both_canonical_and_analytics_tables() -> None:
    text = (ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py").read_text()
    assert "def upsert_canonical_trades" in text
    assert "paper_fill_materializer_v2" in text
    assert "materialized_trade_id" in text
    assert "NULLIF(t.payload->>'strategy','')" in text
    assert "upsert_trades(conn, trades)" in text
    assert "upsert_canonical_trades(conn, trades, legacy_cutoff)" in text
    assert "legacy_cutoff" in text
    assert "refresh_canonical_attribution" in text


def test_scheduler_runs_materializer_with_apply_and_foreground_priority() -> None:
    text = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"PAPER_CLOSED_TRADE_MATERIALIZER_V2"' in text
    assert '["--apply"]' in text
    assert 'EXECUTOR_NICE = {"PAPER_CLOSED_TRADE_MATERIALIZER_V2": 0}' in text


def test_migration_is_idempotent_and_scheduled() -> None:
    text = (ROOT / "sql/analytics/136_paper_closed_trade_materializer_v2.sql").read_text()
    assert "paper_closed_trade_identity_v2" in text
    assert "PRIMARY KEY" in text
    assert "ON CONFLICT(job_code) DO UPDATE" in text
    assert "PAPER_CLOSED_TRADE_MATERIALIZER_V2" in text
