from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sync_failure_is_not_reported_as_success() -> None:
    text=(ROOT/'src/scripts/run_real_portfolio_position_sync.py').read_text()
    assert 'return 2' in text
    assert '_record_sync_state(dsn, "FAILED"' in text
    assert "positions_zeroed" in text
    assert "NOT(symbol=ANY(%s))" in text


def test_safety_monitor_requires_fresh_sync() -> None:
    text=(ROOT/'src/scripts/run_paper_safety_monitor_v1.py').read_text()
    assert 'sync_is_fresh' in text
    assert 'BROKER_POSITION_SYNC_NOT_FRESH' in text


def test_sync_state_is_db_backed() -> None:
    text=(ROOT/'sql/analytics/140_broker_position_sync_state_v1.sql').read_text()
    assert 'broker_position_sync_state_v1' in text
    assert "'HEALTHY','FAILED'" in text
