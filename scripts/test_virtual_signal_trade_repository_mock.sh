#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.storage.virtual_signal_trade_repository import VirtualSignalTradeRepository

calls = []

class FakeCursor:
    def __init__(self, row=None):
        self.row = row
    def execute(self, sql, params=None):
        calls.append((sql, params))
    def fetchone(self):
        return [123] if self.row is None else self.row
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class FakeConn:
    def cursor(self, *args, **kwargs):
        return FakeCursor()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

repo = VirtualSignalTradeRepository(database_url="fake")
repo._connect = lambda: FakeConn()

trade_id = repo.open_trade(
    symbol="BRN6@RTSX",
    side="BUY",
    qty=1,
    entry_price=64.2,
    stop_loss=62.925,
    take_profit=65.9,
)

assert trade_id == 123
assert "INSERT INTO virtual_signal_trades" in calls[0][0]

repo.close_trade(
    trade_id=123,
    exit_price=65.1,
    close_reason="manual_close",
    pnl=0.9,
    r_multiple=0.7,
)

assert "UPDATE virtual_signal_trades" in calls[1][0]

print("VIRTUAL_SIGNAL_TRADE_REPOSITORY_MOCK_OK")
PY
