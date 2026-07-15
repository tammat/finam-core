import importlib.util
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "run_forward_edge_observation_worker_v1.py"
SPEC = importlib.util.spec_from_file_location("forward_edge_worker", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_session_code_uses_moscow_market_hours() -> None:
    assert MODULE.session_code(datetime(2026, 7, 14, 8, tzinfo=timezone.utc)) == "MORNING"
    assert MODULE.session_code(datetime(2026, 7, 14, 12, tzinfo=timezone.utc)) == "DAY"
    assert MODULE.session_code(datetime(2026, 7, 14, 17, tzinfo=timezone.utc)) == "EVENING"


def test_evaluation_watermark_never_moves_before_activation() -> None:
    activated = datetime(2026, 7, 15, 8, 15, 50, tzinfo=timezone.utc)
    older_bar = datetime(2026, 7, 15, 8, 10, tzinfo=timezone.utc)
    newer_bar = datetime(2026, 7, 15, 8, 20, tzinfo=timezone.utc)

    assert MODULE.evaluation_watermark(activated, older_bar) == activated
    assert MODULE.evaluation_watermark(activated, newer_bar) == newer_bar
