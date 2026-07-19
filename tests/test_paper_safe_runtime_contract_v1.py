from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_contract_resolver_uses_fresh_roll_decision_and_calendar() -> None:
    text = (ROOT / "src/scripts/resolve_runtime_contract_v1.py").read_text()
    assert "futures_roll_decision_v1" in text
    assert "futures_contract_calendar" in text
    assert "last_trade_date>=current_date" in text
    assert "interval '24 hours'" in text


def test_paper_safe_resolves_contracts_before_starting_monitor() -> None:
    text = (ROOT / "scripts/run_paper_safe.sh").read_text()
    resolve_position = text.index("resolve_runtime_contract_v1.py --root BR")
    monitor_position = text.index("run_paper_safety_monitor_v1.py")
    assert resolve_position < monitor_position
    assert 'REAL_EXECUTION_SYMBOL_ALLOWLIST="${BR_CONTRACT}"' in text
    assert "BRM6@RTSX" not in text
    assert "NGK6@RTSX" not in text
