from marketcore.research.dynamic_exit_v1 import dynamic_exit_v1, entry_allowed_v1
from scripts.meta_entry_policy_v2 import apply_meta_entry_policy_v2


def test_meta_entry_uses_only_history_and_requires_trend_volume() -> None:
    prices = [100.0 + index for index in range(30)]
    volumes = [100.0] * 29 + [150.0]
    policy = {"entry_policy_code":"META_ENTRY_V1","entry_trend_lookback":10,
              "entry_volatility_lookback":5,"entry_min_volume_ratio":1.2,
              "entry_min_volatility_bps":0,"entry_max_volatility_bps":1000}
    assert entry_allowed_v1(prices, volumes, 29, 1, policy)
    assert not entry_allowed_v1(prices, volumes, 29, -1, policy)


def test_meta_entry_v2_can_observe_missing_volume_without_fabricating_it() -> None:
    prices = [100.0 + index for index in range(30)]
    policy = {"entry_policy_code":"META_ENTRY_V2","entry_trend_lookback":10,
              "entry_volatility_lookback":5,"entry_volume_mode":"OBSERVE",
              "entry_min_volatility_bps":0,"entry_max_volatility_bps":1000}
    assert entry_allowed_v1(prices, [0.0] * 30, 29, 1, policy)


def test_meta_entry_v2_enforces_versioned_regime_filter() -> None:
    prices = [100.0 + index for index in range(30)]
    volumes = [100.0] * 29 + [150.0]
    policy = {
        "entry_policy_code": "META_ENTRY_V2",
        "entry_trend_lookback": 10,
        "entry_volatility_lookback": 5,
        "entry_min_volume_ratio": 1.2,
        "entry_min_volatility_bps": 0,
        "entry_max_volatility_bps": 1000,
        "entry_regime_mode": "REQUIRE",
        "entry_allowed_regimes": ["trend_up_expansion"],
    }
    assert entry_allowed_v1(
        prices, volumes, 29, 1, policy, regime_code="trend_up_expansion"
    )
    assert not entry_allowed_v1(
        prices, volumes, 29, 1, policy, regime_code="range_normal"
    )


def test_adaptive_entry_constraints_override_profile_observe_defaults() -> None:
    profile = {"entry_policy_code": "META_ENTRY_V2", "entry_regime_mode": "OBSERVE"}
    scenario = {
        "entry_policy_code": "META_ENTRY_V2",
        "entry_regime_mode": "REQUIRE",
        "entry_allowed_regimes": ["trend_up"],
    }
    applied = apply_meta_entry_policy_v2(scenario, profile)
    assert applied["entry_regime_mode"] == "REQUIRE"
    assert applied["entry_allowed_regimes"] == ["trend_up"]


def test_dynamic_exit_stops_before_maximum_when_trend_disappears() -> None:
    prices = [100,101,102,103,104,105,106,107,108,107,106,105,104]
    decision = dynamic_exit_v1(prices, 5, 1, 7, {
        "exit_policy_code":"DYNAMIC_EXIT_V1","exit_stop_atr":10,"exit_trail_atr":10,
        "exit_trend_lookback":2,"exit_volatility_risk_multiplier":100,"exit_minimum_bars":2,
    })
    assert decision.exit_index < 12
    assert decision.reason_code == "TREND_GONE"


def test_fixed_and_dynamic_exit_keep_separate_time_contracts() -> None:
    source = __import__("pathlib").Path("src/scripts/build_strategy_execution_runner_v1.py").read_text()
    assert 'exit_max_holding_bars", max(hold, 20)' in source
    assert '== "DYNAMIC_EXIT_V1" else hold' in source
