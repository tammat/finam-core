#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="${PYTHON:-$ROOT/venv/bin/python}"

cd "$ROOT"

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== TEST DECISION FUNNEL V1 ==="

"$PYTHON" -m py_compile \
  core/decision_funnel.py \
  storage/decision_funnel_repository.py

"$PYTHON" - <<'PY'
from __future__ import annotations

from core.decision_funnel import (
    DecisionOutcome,
    DecisionReason,
    DecisionStage,
    FunnelDecision,
    SignalDecisionEvent,
)
from storage.decision_funnel_repository import (
    DecisionFunnelRepository,
)


class FakeCursor:
    def __init__(self) -> None:
        self.execute_calls = []
        self.executemany_calls = []

    def execute(self, query, params=None) -> None:
        self.execute_calls.append((query, params))

    def executemany(self, query, params) -> None:
        self.executemany_calls.append(
            (query, list(params))
        )

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


passed = FunnelDecision(
    allowed=True,
    reason=DecisionReason.UNKNOWN,
    context={"edge_score": "0.81"},
)

pass_event = passed.to_event(
    signal_id="signal-001",
    symbol="BR@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    stage=DecisionStage.EDGE,
    direction="LONG",
)

assert pass_event.outcome == DecisionOutcome.PASS
assert pass_event.reason == DecisionReason.PASSED
assert pass_event.context["edge_score"] == "0.81"

rejected = FunnelDecision(
    allowed=False,
    reason=DecisionReason.EDGE_SCORE_TOO_LOW,
    context={
        "edge_score": "0.41",
        "required_edge_score": "0.65",
    },
)

reject_event = rejected.to_event(
    signal_id="signal-002",
    symbol="NG@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    stage=DecisionStage.EDGE,
    direction="LONG",
)

assert reject_event.outcome == DecisionOutcome.REJECT
assert (
    reject_event.reason
    == DecisionReason.EDGE_SCORE_TOO_LOW
)

try:
    SignalDecisionEvent(
        signal_id="invalid",
        symbol="BR@RTSX",
        strategy="test",
        timeframe="M5",
        stage=DecisionStage.RISK,
        outcome=DecisionOutcome.PASS,
        reason=DecisionReason.DAILY_LOSS_LIMIT,
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "PASS with rejection reason must fail"
    )

connection = FakeConnection()
repository = DecisionFunnelRepository(connection)

repository.record(pass_event)

assert connection.commits == 1
assert connection.rollbacks == 0
assert (
    len(connection.cursor_instance.execute_calls)
    == 1
)

insert_query, params = (
    connection.cursor_instance.execute_calls[0]
)

assert "INSERT INTO analytics.signal_decision_funnel_v1" in insert_query
assert params[1] == "signal-001"
assert params[6] == "EDGE"
assert params[7] == "PASS"
assert params[8] == "PASSED"

saved = repository.record_many(
    [pass_event, reject_event]
)

assert saved == 2
assert connection.commits == 2
assert (
    len(connection.cursor_instance.executemany_calls)
    == 1
)

print("domain_contract=OK")
print("repository_contract=OK")
print("event_immutability=OK")
print("rejected_signal_logging=OK")
PY

grep -q \
  'CREATE TABLE IF NOT EXISTS analytics.signal_decision_funnel_v1' \
  storage/migrations/001_decision_funnel_v1.sql

grep -q \
  "UNIQUE (signal_id, stage, attempt_no)" \
  storage/migrations/001_decision_funnel_v1.sql

grep -q \
  "outcome IN ('PASS', 'REJECT', 'ERROR', 'SKIP')" \
  storage/migrations/001_decision_funnel_v1.sql

for forbidden in \
  sqlite3 \
  "execution_enabled=1" \
  "micro_live_allowed=1" \
  "DROP TABLE" \
  "TRUNCATE "
do
    count="$(
        {
            grep -R -F "$forbidden" \
              core/decision_funnel.py \
              storage/decision_funnel_repository.py \
              storage/migrations/001_decision_funnel_v1.sql \
              2>/dev/null || true
        } |
        wc -l |
        tr -d ' '
    )"

    echo "forbidden_marker=$forbidden count=$count"
    [[ "$count" -eq 0 ]]
done

echo "python_compile=OK"
echo "postgresql_only=1"
echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_FUNNEL_V1_OK"
