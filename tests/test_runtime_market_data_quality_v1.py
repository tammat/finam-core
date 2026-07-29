from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quality_view_is_session_aware_completed_bar_and_fail_closed() -> None:
    sql = (ROOT / "sql/analytics/222_runtime_market_data_quality_v1.sql").read_text()
    assert "runtime_market_data_quality_v1" in sql
    assert "ts + p.interval_seconds*interval '1 second' <= p.now_utc" in sql
    for code in ("OUT_OF_SESSION", "NO_COMPLETED_BARS", "STALE", "GAP", "COST_SPEC_STALE", "READY"):
        assert code in sql


def test_contract_specs_refresh_hourly_during_market_day() -> None:
    sql = (ROOT / "sql/analytics/222_runtime_market_data_quality_v1.sql").read_text()
    assert "CONTRACT_SPEC_SYNC_INTRADAY" in sql
    assert "interval_minutes=60" in sql
