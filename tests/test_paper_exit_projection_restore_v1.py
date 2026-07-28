from pathlib import Path


def test_exit_engine_restores_isolated_projection_before_reading_position_qty() -> None:
    """A restarted Paper process must still be able to close its DB-backed position."""
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")
    start = source.index("    def _build_exit_intent_if_any(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    restore = body.index("self._restore_pm_position_from_projection_v1(symbol)")
    read_qty = body.index("qty = self._position_qty_for_symbol(symbol)")
    assert restore < read_qty


def test_projection_restore_preserves_paper_position_open_time() -> None:
    """A restart must not restart the minimum-hold timer for an existing Paper position."""
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")
    start = source.index("    def _restore_pm_position_from_projection_v1(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert "lifecycle.created_at AS opened_at" in body
    assert 'exit_state["opened_at_ts"] = float(opened_at.timestamp())' in body
    assert 'exit_state["last_qty"] = projection_qty' in body


def test_projection_restore_reconstructs_completed_bar_clock() -> None:
    """A restart must not move the max-bars safety horizon backwards."""
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")
    start = source.index("    def _restore_pm_position_from_projection_v1(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]

    assert "COUNT(*)::integer AS bars_held" in body
    assert "b.ts > lifecycle.created_at" in body
    assert "b.ts + CASE" in body
    assert 'exit_state["bars_held"] = max(' in body
    assert 'exit_state["last_exit_closed_bar_key"] = last_bar_ts.isoformat()' in body
