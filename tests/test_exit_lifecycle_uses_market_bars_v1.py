from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_exit_lifecycle_counts_completed_bars_not_quotes() -> None:
    text = (ROOT / "src/finam_core/execution/exit_lifecycle_manager.py").read_text()
    assert 'bar_bucket = int(time.time() // bar_seconds)' in text
    assert 'is_new_completed_bar' in text
    assert 'state["bars_held"] = int(state.get("bars_held") or 0) + 1' in text
    assert 'prev_close=state.get("prev_close") if is_new_completed_bar else None' in text
    assert 'state["bars_held"] = int(state.get("bars_held") or 0) + 1\n        state["last_qty"]' not in text
