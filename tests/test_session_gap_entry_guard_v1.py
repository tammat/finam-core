from datetime import datetime, timezone
from types import SimpleNamespace

from finam_core.risk.session_gap_entry_guard_v1 import SessionGapEntryGuardV1


class Guard(SessionGapEntryGuardV1):
    def __init__(self):
        self._logger = None
        self._policy_cache = {}
        self._history = {}
        self._confirmation_remaining = {}

    def _policy(self, key):
        return {
            "atr_lookback": 5,
            "elevated_gap_atr": 1.5,
            "extreme_gap_atr": 3.0,
            "confirmation_bars": 2,
        }

    def _load_history(self, bar, policy):
        return [(101.0, 99.0, 100.0)] * 6

    def _finish(self, bar, decision, previous_close, atr):
        return decision


def bar(open_price=100.0):
    return SimpleNamespace(
        symbol="SBER@MISX",
        timeframe="M5",
        ts=datetime.now(timezone.utc),
        open=open_price,
        high=open_price + 1,
        low=open_price - 1,
        close_price=open_price,
    )


def test_normal_gap_allows_entry():
    assert Guard().evaluate(bar(100.5)).allowed


def test_extreme_gap_blocks_and_requires_closed_bar_confirmation():
    guard = Guard()
    first = guard.evaluate(bar(107.0))
    second = guard.evaluate(bar(107.0))
    third = guard.evaluate(bar(107.0))
    fourth = guard.evaluate(bar(107.0))
    assert first.reason_code == "EXTREME_SESSION_GAP"
    assert second.reason_code == "GAP_CONFIRMATION_PENDING"
    assert third.reason_code == "GAP_CONFIRMATION_PENDING"
    assert fourth.allowed


def test_policy_missing_fails_closed():
    guard = Guard()
    guard._policy = lambda key: None
    decision = guard.evaluate(bar())
    assert not decision.allowed
    assert decision.reason_code == "GAP_POLICY_MISSING"
