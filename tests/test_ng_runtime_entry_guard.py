from finam_core.strategy.futures.ng_runtime_entry_guard import evaluate_ng_entry_guard


def test_ng_is_blocked_when_universe_disables_all_contracts():
    result = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=(), kill_switch_active=False, seconds_since_last=None)
    assert not result.allowed and result.reason == "NG_RUNTIME_UNIVERSE_DISABLED"


def test_only_canonical_enabled_contract_is_allowed():
    wrong = evaluate_ng_entry_guard(symbol="NGU6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=False, seconds_since_last=None)
    right = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=False, seconds_since_last=None)
    assert not wrong.allowed and right.allowed


def test_kill_switch_prevents_signal_churn():
    result = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=True, seconds_since_last=None)
    assert result.reason == "KILL_SWITCH_ACTIVE_PRE_SIGNAL"


def test_cooldown_blocks_repeated_entry():
    result = evaluate_ng_entry_guard(symbol="NGQ6@RTSX", enabled_symbols=("NGQ6@RTSX",), kill_switch_active=False, seconds_since_last=20, cooldown_seconds=180)
    assert not result.allowed and result.reason == "NG_ENTRY_COOLDOWN"
