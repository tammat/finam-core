from __future__ import annotations

from decimal import Decimal
import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "src" / "scripts" / "signal_funnel_analytics_v1.py"
SPEC = importlib.util.spec_from_file_location("signal_funnel_analytics_v1", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_stage_signature_ignores_labels_and_evidence() -> None:
    stages = [
        ("SIGNALS", "Signals", Decimal("10"), {"source": "a"}),
        ("FILLS", "Fills", Decimal("4"), {"source": "b"}),
    ]

    assert MODULE.stage_signature(stages) == [
        ("SIGNALS", Decimal("10")),
        ("FILLS", Decimal("4")),
    ]
