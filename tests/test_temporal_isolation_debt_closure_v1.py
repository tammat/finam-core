from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_legacy_results_are_quarantined_and_cannot_promote() -> None:
    sql=(ROOT/"sql/analytics/234_pre_purging_result_quarantine_v1.sql").read_text()
    assert "LEGACY_PRE_PURGING" in sql
    assert "promotion_allowed=false" in sql
    promoter=(ROOT/"src/scripts/promote_regime_oos_to_canonical_v1.py").read_text()
    assert "AND h.promotion_allowed" in promoter


def test_remaining_replay_and_legacy_oos_have_embargo() -> None:
    replay=(ROOT/"src/scripts/run_targeted_trade_level_replay_v1.py").read_text()
    assert "purged_bar_window" in replay and "embargo" in replay
    legacy=(ROOT/"src/scripts/research/build_out_of_sample_validation_engine_v1.py").read_text()
    assert "LEGACY_OOS_EMBARGO_SECONDS" in legacy
    assert "ct.entry_ts > s.last_trade" in legacy


def test_swing_forward_and_br_artifact_gate_are_purged() -> None:
    swing=(ROOT/"src/scripts/run_swing_autonomous_lifecycle_v1.py").read_text()
    assert "embargo_boundary" in swing and "label_horizon_bars" in swing
    br=(ROOT/"src/scripts/build_br_rolling_swing_artifact_stability_gate_v1.py").read_text()
    assert "r[2]<right" in br
    assert "next_entry_index=exit_i" in br


def test_global_trade_once_policy_is_explicit() -> None:
    sql=(ROOT/"sql/analytics/231_v5_purged_oos_worker_v1.sql").read_text()
    assert "V5_OOS_GLOBAL_TRADE_ONCE" in sql
    assert "GLOBAL_SOURCE_TRADE" in sql
