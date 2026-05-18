#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/replay/replay_campaign_telemetry.py

python - <<'PY'
from datetime import datetime, timezone

from finam_core.replay.replay_campaign_telemetry import (
    ReplayCampaignTelemetry,
)


class FakeCursor:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))


class FakeConn:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.commits += 1


class FakePg:
    def __init__(self):
        self.conn = FakeConn()

    def _connect(self):
        return self.conn


pg = FakePg()

telemetry = ReplayCampaignTelemetry(pg)

telemetry.log_run(
    campaign_id="campaign-1",
    replay_id="replay-1",
    symbol="BRM6@RTSX",
    timeframe="M5",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    status="success",
    started_at=datetime.now(timezone.utc),
    finished_at=datetime.now(timezone.utc),
    duration_sec=1.5,
    return_code=0,
    command="python replay.py",
)

assert pg.conn.commits == 1
assert len(pg.conn.cursor_obj.calls) == 1

sql, params = pg.conn.cursor_obj.calls[0]

assert "replay_campaign_runs" in sql
assert params[0] == "campaign-1"
assert params[1] == "replay-1"
assert params[2] == "BRM6@RTSX"

print("OK: replay campaign telemetry")
PY
