from pathlib import Path

from finam_core.pipelines.paper_pipeline import entry_closed_bar_evaluation_due_v1


def test_entry_evaluation_runs_once_per_completed_m5_bar():
    cache: dict[str, int] = {}

    assert entry_closed_bar_evaluation_due_v1(cache, "SBER@MISX", now_epoch=601.0)
    assert not entry_closed_bar_evaluation_due_v1(cache, "SBER@MISX", now_epoch=899.9)
    assert entry_closed_bar_evaluation_due_v1(cache, "SBER@MISX", now_epoch=900.0)
    assert entry_closed_bar_evaluation_due_v1(cache, "GAZP@MISX", now_epoch=900.0)


def test_exit_route_precedes_entry_bar_return():
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

    exit_route = source.index("exit_raw_intent = self._build_exit_intent_if_any")
    entry_gate = source.index("PIPE_ENTRY_WAIT_NEXT_CLOSED_BAR")
    strategy_route = source.index("# === STRATEGY SELECTION (FIXED REGIME V2)")

    assert exit_route < entry_gate < strategy_route
