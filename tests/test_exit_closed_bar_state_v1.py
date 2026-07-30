from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "src/finam_core/pipelines/paper_pipeline.py"


def test_exit_bar_counter_is_advanced_from_closed_bar_route_only() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    recorder_start = source.index("    def _record_live_quote_to_storage(")
    recorder_end = source.index("\n    def ", recorder_start + 10)
    recorder = source[recorder_start:recorder_end]
    exit_start = source.index("    def _build_exit_intent_if_any(")
    exit_end = source.index("\n    def ", exit_start + 10)
    exit_body = source[exit_start:exit_end]

    assert "self._mark_exit_closed_bar_v1(bar)" in recorder
    assert 'state["bars_held"] = int(state.get("bars_held") or 0) + 1' not in exit_body
    assert 'bars_for_exit = int(state["bars_held"]) if is_completed_bar else 0' in exit_body


def test_regime_invalidation_requires_confirmed_fresh_candle_regime() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    start = source.index("    def _mark_exit_closed_bar_v1(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert '== "CANDLE_REGIME_V3"' in body
    assert 'getattr(regime, "data_ready"' in body
    assert 'getattr(regime, "stale"' in body
    assert 'getattr(regime, "confirmed_bars"' in body
    assert '"regime_invalidation_long"' in body
    assert '"regime_invalidation_short"' in body


def test_regime_invalidation_cannot_bypass_minimum_hold() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    start = source.index("    def _build_exit_intent_if_any(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert "regime_exit_reason and position_age_sec >= min_hold_sec" in body
    assert "PIPE_REGIME_EXIT_MIN_HOLD_GUARD" in body


def test_new_entry_resets_previous_position_exit_clock() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    start = source.index("    def _mark_anti_reentry_entry(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert '"bars_held": 0' in body
    assert '"regime_exit_reason": None' in body
    assert '"opened_at_ts": time.time()' in body


def test_ng_directional_guard_is_wired_before_paper_entry() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    assert "evaluate_ng_directional_entry_guard(" in source
    assert "PIPE_NG_DIRECTIONAL_ENTRY_BLOCK" in source
    assert '"_ng_consumed_entry_bar_fingerprints_v1"' in source


def test_time_exit_is_a_long_horizon_safety_net_for_energy() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    start = source.index("    def _exit_engine_for_symbol(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert 'os.getenv("ENERGY_MAX_BARS_IN_TRADE", "60")' in body
    assert "max_bars_in_trade=max_bars" in body


def test_persisted_regime_bar_is_the_no_trade_progress_fallback() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    start = source.index("    def _sync_exit_closed_bar_from_regime_v1(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert "candle_regime_engine_v2.evaluate(symbol, timeframe)" in body
    assert "last_exit_closed_bar_key" in body
    assert 'state["bars_held"] = int(state.get("bars_held") or 0) + 1' in body

    exit_start = source.index("    def _build_exit_intent_if_any(")
    exit_end = source.index("\n    def ", exit_start + 10)
    exit_body = source[exit_start:exit_end]
    assert "self._sync_exit_closed_bar_from_regime_v1(symbol)" in exit_body
