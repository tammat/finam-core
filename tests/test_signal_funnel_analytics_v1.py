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


def test_funnel_counts_unique_bar_opportunities_and_shadow_separately() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "SIGNAL_FUNNEL_ANALYTICS_V5_UNIQUE_CLOSED_BAR_OPPORTUNITY" in source
    assert "opportunity_key" in source
    assert "regime_bar_ts" in source
    assert "date_bin(" in source
    assert 'code in {"SHADOW", "ORDERS"}' in source
    assert '("EVALUATIONS", "Все проверки условий"' in source
    assert '("SIGNALS", "Уникальные возможности на закрытом баре"' in source
    assert '("SHADOW", "Возможности, оценённые в Shadow"' in source
    assert '"not_an_edge_loss": True' in source
