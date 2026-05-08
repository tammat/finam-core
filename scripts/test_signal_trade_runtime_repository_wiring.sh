#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.simulation.signal_trade_runtime import SignalTradeRuntime

signals = []

class FakeNotifier:
    def send_signal(self, **kwargs):
        signals.append(kwargs)
        return True

    def send_text(self, text):
        return True

class FakeRepo:
    def __init__(self):
        self.opened = []

    def open_trade(self, **kwargs):
        self.opened.append(kwargs)
        return 777

runtime = SignalTradeRuntime(FakeNotifier())
runtime.trade_repo = FakeRepo()

res = runtime.register_signal(
    symbol="BRN6@RTSX",
    side="BUY",
    entry=64.2,
    stop_loss=62.925,
    take_profit=65.9,
    qty=1,
    confidence=0.7,
    regime="test",
    reason="test_signal",
)

assert res["status"] == "OPENED", res
assert res["repo_trade_id"] == 777, res
assert len(runtime.trade_repo.opened) == 1
assert runtime.trade_repo.opened[0]["symbol"] == "BRN6@RTSX"
assert runtime.trade_repo.opened[0]["entry_price"] == 64.2

print("SIGNAL_TRADE_RUNTIME_REPOSITORY_WIRING_OK")
PY
