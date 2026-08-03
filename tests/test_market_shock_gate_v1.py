from pathlib import Path

from finam_core.risk.market_shock_gate_v1 import decide_market_shock_gate_v1


def decide(level: str, **overrides):
    values = dict(
        intent_type="ENTRY", risk_level=level, completed_m15_bars=4,
        gap_atr=0.8, spread_atr=0.04, relative_volume=1.0,
        market_context_fresh=True, recovery_policy_validated=True,
    )
    values.update(overrides)
    return decide_market_shock_gate_v1(**values)


def test_shock_and_elevated_are_shadow_only_and_exit_is_always_allowed() -> None:
    assert (decide("SHOCK").allowed, decide("SHOCK").mode) == (False, "SHADOW_ONLY")
    assert (decide("ELEVATED").allowed, decide("ELEVATED").mode) == (False, "SHADOW_ONLY")
    assert decide("SHOCK", intent_type="EXIT").allowed


def test_recovery_requires_bars_context_gap_spread_and_volume() -> None:
    assert decide("RECOVERY").allowed
    assert decide("RECOVERY", completed_m15_bars=3).reason == "RECOVERY_M15_INSUFFICIENT"
    assert decide("RECOVERY", market_context_fresh=False).reason == "RECOVERY_MARKET_CONTEXT_STALE"
    assert decide("RECOVERY", gap_atr=1.6).reason == "RECOVERY_GAP_TOO_LARGE_OR_UNKNOWN"
    assert decide("RECOVERY", spread_atr=0.11).reason == "RECOVERY_SPREAD_TOO_WIDE_OR_UNKNOWN"
    assert decide("RECOVERY", relative_volume=0.69).reason == "RECOVERY_VOLUME_TOO_LOW_OR_UNKNOWN"
    assert decide("RECOVERY", recovery_policy_validated=False).reason == "RECOVERY_POLICY_NOT_VALIDATED"


def test_runtime_and_ui_integrate_gate_without_changing_paper_profile() -> None:
    pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
    ui = Path(
        "src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"
    ).read_text()
    sql = Path("sql/analytics/250_market_event_shock_gate_v1.sql").read_text()
    assert "PIPE_MARKET_SHOCK_GATE_BLOCK" in pipeline
    assert "self._reject_persisted_signal_v1(intent, f\"market_shock_gate:{shock_reason}\")" in pipeline
    assert "Риск событий" in ui and "биржа закрыта по календарю" in ui
    assert "market_shock_gate_audit_v1" in sql
    assert "paper_profile_changed=0" in pipeline


def test_readiness_does_not_turn_scoped_event_into_global_shadow_only() -> None:
    source = Path("src/scripts/analytics/build_monday_readiness_v1.py").read_text()
    assert "event_is_global='*' in patterns" in source
    assert "risk in {'SHOCK','ELEVATED'} and event_is_global" in source
    assert "runtime_per_symbol_gate_required" in source
