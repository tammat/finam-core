from datetime import datetime
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from zoneinfo import ZoneInfo

_MODULE_PATH = (
    Path(__file__).parents[1]
    / "src/finam_core/execution/runtime_edge_governance_soft_block_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("runtime_edge_governance_under_test", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
RuntimeEdgeGovernanceSoftBlockV1 = _MODULE.RuntimeEdgeGovernanceSoftBlockV1


class _SessionGate:
    def decide(self, **_kwargs):
        return SimpleNamespace(
            allowed=True,
            action="ALLOW",
            expectancy_points=None,
            closed_trades=None,
        )


class _StrictGate:
    def __init__(self, reason: str):
        self.reason = reason

    def evaluate(self, **_kwargs):
        return SimpleNamespace(
            allowed=False,
            reason=self.reason,
            expectancy_points=None,
            closed_trades=0,
        )


def _governance(reason: str) -> RuntimeEdgeGovernanceSoftBlockV1:
    governance = RuntimeEdgeGovernanceSoftBlockV1.__new__(
        RuntimeEdgeGovernanceSoftBlockV1
    )
    governance.session_gate = _SessionGate()
    governance.strict_gate = _StrictGate(reason)
    governance._decay_state_for = lambda **_kwargs: (None, None, None)
    return governance


def _decide(governance, *, evidence_accumulation: bool):
    return governance.decide(
        symbol="SBER@MISX",
        side="BUY",
        strategy="MEAN_REVERSION_EQUITY",
        timeframe="M5",
        regime="range_low_vol",
        session_name="московская_середина",
        ts=datetime(2026, 7, 25, 12, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        evidence_accumulation=evidence_accumulation,
    )


def test_missing_rule_allows_only_explicit_evidence_accumulation():
    governance = _governance("strict_mode_no_match")

    blocked = _decide(governance, evidence_accumulation=False)
    accumulating = _decide(governance, evidence_accumulation=True)

    assert blocked.allowed is False
    assert blocked.reason == "strict_gate_block"
    assert accumulating.allowed is True
    assert accumulating.action == "ALLOW_ACCUMULATION"
    assert accumulating.reason == "strict_gate_evidence_accumulation"


def test_low_sample_can_accumulate_but_negative_rule_stays_blocked():
    low_sample = _decide(
        _governance("strict_mode_low_sample"),
        evidence_accumulation=True,
    )
    negative = _decide(
        _governance("strict_mode_negative_expectancy"),
        evidence_accumulation=True,
    )

    assert low_sample.allowed is True
    assert low_sample.action == "ALLOW_ACCUMULATION"
    assert negative.allowed is False
    assert negative.reason == "strict_gate_block"
