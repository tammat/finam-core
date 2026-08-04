#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="${PYTHON:-$ROOT/venv/bin/python}"

cd "$ROOT"

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== TEST DECISION FUNNEL READ MODEL V1 ==="

"$PYTHON" -m py_compile \
  storage/decision_funnel_read_model.py

"$PYTHON" - <<'PY'
from __future__ import annotations

from datetime import datetime, timezone

from storage.decision_funnel_read_model import (
    DecisionFunnelReadModelBuilder,
    DecisionFunnelReadModelFilter,
    STAGE_ORDER,
)


class FakeCursor:
    def __init__(self, result_sets):
        self._result_sets = list(result_sets)
        self._current = None
        self.execute_calls = []

    def execute(self, query, params=None):
        self.execute_calls.append((query, params))

        if not self._result_sets:
            raise AssertionError(
                "unexpected execute call"
            )

        self._current = self._result_sets.pop(0)

    def fetchone(self):
        if isinstance(self._current, dict):
            return self._current

        raise AssertionError(
            "fetchone expected dictionary result"
        )

    def fetchall(self):
        if isinstance(self._current, list):
            return self._current

        raise AssertionError(
            "fetchall expected list result"
        )


class FakeConnection:
    def __init__(self, result_sets):
        self.cursor_instance = FakeCursor(
            result_sets
        )
        self.closed = 0

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed += 1


NOW = datetime(
    2026,
    8,
    4,
    12,
    0,
    tzinfo=timezone.utc,
)

FILTERS = DecisionFunnelReadModelFilter.last_hours(
    24,
    now=NOW,
)

empty_connection = FakeConnection(
    [
        {
            "event_count": 0,
            "signal_count": 0,
            "symbol_count": 0,
            "strategy_count": 0,
            "first_event_at": None,
            "last_event_at": None,
            "pass_events": 0,
            "reject_events": 0,
            "error_events": 0,
            "skip_events": 0,
        },
        [],
        [],
        [],
        [],
    ]
)

empty_model = DecisionFunnelReadModelBuilder(
    lambda: empty_connection
).build(FILTERS)

assert empty_model["status"] == "EMPTY"
assert empty_model["read_only"] is True
assert empty_model["summary"]["event_count"] == 0
assert empty_model["summary"]["signal_count"] == 0
assert len(empty_model["stage_funnel"]) == len(
    STAGE_ORDER
)
assert all(
    row["signal_count"] == 0
    for row in empty_model["stage_funnel"]
)
assert empty_connection.closed == 1
assert (
    len(
        empty_connection
        .cursor_instance
        .execute_calls
    )
    == 5
)

filled_connection = FakeConnection(
    [
        {
            "event_count": 13,
            "signal_count": 5,
            "symbol_count": 2,
            "strategy_count": 2,
            "first_event_at": NOW,
            "last_event_at": NOW,
            "pass_events": 8,
            "reject_events": 5,
            "error_events": 0,
            "skip_events": 0,
        },
        [
            {
                "stage": "STRATEGY",
                "event_count": 5,
                "signal_count": 5,
                "passed_signals": 4,
                "rejected_signals": 1,
                "error_signals": 0,
                "skipped_signals": 0,
            },
            {
                "stage": "EDGE",
                "event_count": 4,
                "signal_count": 4,
                "passed_signals": 2,
                "rejected_signals": 2,
                "error_signals": 0,
                "skipped_signals": 0,
            },
            {
                "stage": "RISK",
                "event_count": 2,
                "signal_count": 2,
                "passed_signals": 1,
                "rejected_signals": 1,
                "error_signals": 0,
                "skipped_signals": 0,
            },
            {
                "stage": "RUNTIME",
                "event_count": 2,
                "signal_count": 2,
                "passed_signals": 1,
                "rejected_signals": 1,
                "error_signals": 0,
                "skipped_signals": 0,
            },
        ],
        [
            {
                "stage": "EDGE",
                "reason_code": "EDGE_SCORE_TOO_LOW",
                "event_count": 2,
                "signal_count": 2,
                "last_seen_at": NOW,
            },
            {
                "stage": "RUNTIME",
                "reason_code": "MICRO_LIVE_NOT_ALLOWED",
                "event_count": 1,
                "signal_count": 1,
                "last_seen_at": NOW,
            },
        ],
        [
            {
                "symbol": "BR@RTSX",
                "strategy": "BR_BREAKOUT",
                "timeframe": "M5",
                "event_count": 8,
                "signal_count": 3,
                "rejected_signals": 2,
                "filled_signals": 0,
                "last_event_at": NOW,
            }
        ],
        [
            {
                "event_id": "event-1",
                "signal_id": "signal-1",
                "symbol": "BR@RTSX",
                "strategy": "BR_BREAKOUT",
                "timeframe": "M5",
                "direction": "LONG",
                "stage": "EDGE",
                "outcome": "REJECT",
                "reason_code": "EDGE_SCORE_TOO_LOW",
                "attempt_no": 1,
                "source": "TRADING_ENGINE",
                "context": {
                    "edge_score": "0.41",
                },
                "occurred_at": NOW,
            }
        ],
    ]
)

filled_model = DecisionFunnelReadModelBuilder(
    lambda: filled_connection
).build(FILTERS)

assert filled_model["status"] == "READY"
assert filled_model["summary"]["event_count"] == 13
assert filled_model["summary"]["signal_count"] == 5
assert (
    filled_model["summary"]["rejection_rate"]
    == "0.3846"
)

stage_map = {
    row["stage"]: row
    for row in filled_model["stage_funnel"]
}

assert stage_map["STRATEGY"]["signal_count"] == 5
assert stage_map["STRATEGY"]["pass_rate"] == "0.8000"

assert stage_map["REGIME"]["signal_count"] == 0
assert (
    stage_map["REGIME"][
        "conversion_from_previous_stage"
    ]
    is None
)

assert stage_map["EDGE"]["signal_count"] == 4
assert (
    stage_map["EDGE"]["previous_observed_stage"]
    == "STRATEGY"
)
assert (
    stage_map["EDGE"][
        "conversion_from_previous_stage"
    ]
    == "0.8000"
)

assert stage_map["RISK"]["signal_count"] == 2
assert stage_map["RISK"]["pass_rate"] == "0.5000"

assert (
    filled_model["top_rejection_reasons"][0][
        "reason_code"
    ]
    == "EDGE_SCORE_TOO_LOW"
)

assert (
    filled_model["dimensions"][0]["symbol"]
    == "BR@RTSX"
)

assert (
    filled_model["recent_events"][0]["context"][
        "edge_score"
    ]
    == "0.41"
)

assert (
    filled_model["metadata"][
        "runtime_instrumentation"
    ]
    == 0
)
assert (
    filled_model["metadata"][
        "execution_actions_allowed"
    ]
    == 0
)

assert filled_connection.closed == 1

try:
    DecisionFunnelReadModelFilter.last_hours(
        0,
        now=NOW,
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "zero-hour filter must fail"
    )

try:
    DecisionFunnelReadModelFilter.last_hours(
        24,
        now=NOW,
        recent_limit=501,
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "recent_limit above 500 must fail"
    )

print("empty_state_contract=OK")
print("filled_state_contract=OK")
print("stage_order_contract=OK")
print("conversion_contract=OK")
print("rejection_reason_contract=OK")
print("dimension_contract=OK")
print("recent_event_contract=OK")
print("filter_validation=OK")
print("connection_close_contract=OK")
PY

for marker in \
  "INSERT " \
  "UPDATE " \
  "DELETE " \
  "TRUNCATE " \
  "DROP " \
  "ALTER " \
  ".commit(" \
  "systemctl" \
  "subprocess" \
  "sqlite3" \
  "send_order" \
  "place_order" \
  "submit_order"
do
    count="$(
        {
            grep -F "$marker" \
              storage/decision_funnel_read_model.py \
              2>/dev/null || true
        } |
        wc -l |
        tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$count"
    [[ "$count" -eq 0 ]]
done

grep -q \
  'FROM analytics.signal_decision_funnel_v1' \
  storage/decision_funnel_read_model.py

grep -q \
  '"runtime_instrumentation": 0' \
  storage/decision_funnel_read_model.py

grep -q \
  '"write_actions_allowed": 0' \
  storage/decision_funnel_read_model.py

echo "python_compile=OK"
echo "read_only=1"
echo "runtime_instrumentation=0"
echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_FUNNEL_READ_MODEL_V1_OK"
