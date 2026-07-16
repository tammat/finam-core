from pathlib import Path


def test_cycle_refreshes_decisions_without_trading() -> None:
    source = Path("src/scripts/run_operator_decision_workspace_cycle_v2.py").read_text()
    assert "build_decisions()" in source
    assert "build_lineage" not in source
    assert 'print("runtime_changed=0")' in source
    assert 'print("execution_changed=0")' in source
    assert 'print("live_allowed=0")' in source


def test_timer_runs_every_minute_with_trading_disabled() -> None:
    service = Path("deploy/systemd/marketcore-operator-decision-workspace.service").read_text()
    timer = Path("deploy/systemd/marketcore-operator-decision-workspace.timer").read_text()
    assert "REAL_TRADING_ENABLED=0" in service
    assert "OnUnitActiveSec=1min" in timer
