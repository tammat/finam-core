from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_paper_safe_no_longer_runs_market_pipeline() -> None:
    text = (ROOT / "scripts/run_paper_safe.sh").read_text()
    assert "run_paper_safety_monitor_v1.py" in text
    assert "run_market_pipeline.py" not in text
    assert "--enable-filter-engine" not in text


def test_monitor_is_observational_and_fail_closed() -> None:
    text = (ROOT / "src/scripts/run_paper_safety_monitor_v1.py").read_text()
    assert "sync_broker_positions" in text
    assert "PAPER_SAFETY_MONITOR_REQUIRES_REAL_EXECUTION_DISABLED" in text
    assert "real_portfolio_positions" in text
    assert "REAL_EXECUTION_ENABLED" in text
    assert "REAL_EXECUTION_SYMBOL_ALLOWLIST" in text
    assert "in allowlist" in text
    assert "place_order" not in text
    assert "execute_order" not in text


def test_monitor_state_is_database_backed() -> None:
    text = (ROOT / "sql/analytics/139_paper_safety_monitor_v1.sql").read_text()
    assert "paper_safety_monitor_v1" in text
    assert "HEALTHY" in text
    assert "ALERT" in text
