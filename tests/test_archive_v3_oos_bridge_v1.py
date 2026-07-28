from scripts.build_archive_v3_oos_bridge_v1 import archive_match, linkage_key, root_symbol


def _link(**overrides):
    value = {
        "scope_code": "FRESH_V3_EQUITY", "symbol": "X5@MISX",
        "strategy_code": "VOLATILITY_BREAKOUT_EQUITY", "side_code": "LONG",
        "session_code": "вне_основной_сессии", "regime_code": "trend_up_high_vol",
        "exit_rule": "STOP_TAKE",
    }
    value.update(overrides)
    return value


def test_linkage_key_is_stable_for_normalized_values():
    assert linkage_key(_link()) == linkage_key(_link(symbol="x5@misx"))


def test_archive_match_does_not_call_opposite_side_exact():
    hypothesis = {
        "hypothesis_id": "h1", "symbol": "X5", "strategy_code": "VOLATILITY_BREAKOUT_EQUITY",
        "side_code": "SHORT", "session_code": "вне_основной_сессии",
        "regime_code": "trend_up_high_vol", "holding_code": "STOP_TAKE", "priority_score": 10,
    }
    selected, code = archive_match(_link(), [hypothesis])
    assert selected == hypothesis
    assert code == "RELATED"


def test_archive_match_requires_same_strategy_family():
    selected, code = archive_match(_link(), [{"strategy_code": "EMA_TREND", "priority_score": 99}])
    assert selected is None
    assert code == "V3_ONLY"


def test_futures_contract_is_normalized_to_root():
    assert root_symbol("BRQ6@RTSX") == "BR"
