from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quality_view_is_session_aware_completed_bar_and_fail_closed() -> None:
    sql = (ROOT / "sql/analytics/222_runtime_market_data_quality_v1.sql").read_text()
    assert "runtime_market_data_quality_v1" in sql
    assert "ts + p.interval_seconds*interval '1 second' <= p.now_utc" in sql
    assert "date_trunc('day',p.now_msk) AT TIME ZONE 'Europe/Moscow'" in sql
    for symbol in ("IMOEX2", "RVI", "MXU6@RTSX"):
        assert symbol in sql
    for code in ("OUT_OF_SESSION", "NO_COMPLETED_BARS", "STALE", "GAP", "COST_SPEC_STALE", "READY"):
        assert code in sql


def test_contract_specs_refresh_hourly_during_market_day() -> None:
    sql = (ROOT / "sql/analytics/222_runtime_market_data_quality_v1.sql").read_text()
    assert "CONTRACT_SPEC_SYNC_INTRADAY" in sql
    assert "interval_minutes=60" in sql


def test_regime_feeds_do_not_require_trading_cost_specs() -> None:
    sql = (ROOT / "sql/analytics/222_runtime_market_data_quality_v1.sql").read_text()
    assert "requires_cost_spec" in sql
    assert "WHEN requires_cost_spec AND symbol LIKE '%@RTSX'" in sql
