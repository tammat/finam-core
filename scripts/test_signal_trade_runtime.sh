#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.simulation.signal_trade_runtime import SignalTradeRuntime

signals = []
texts = []

class FakeNotifier:
    def send_signal(self, **kwargs):
        signals.append(kwargs)
        return True

    def send_text(self, text):
        texts.append(text)
        return True

runtime = SignalTradeRuntime(FakeNotifier())

class FakeRouter:
    def send(self, *, trigger, text):
        texts.append(text)
        return True

runtime.notification_router = FakeRouter()

opened = runtime.register_signal(
    symbol="BRN6@RTSX",
    side="BUY",
    entry=80.0,
    stop_loss=79.0,
    take_profit=82.0,
    qty=1,
    confidence=0.8,
    regime="test",
    reason="test_signal",
)

assert opened["status"] == "OPENED", opened
assert opened["telegram_sent"] is True, opened
assert len(signals) == 1, signals

closed = runtime.on_quote(symbol="BRN6@RTSX", price=82.1)

assert len(closed) == 1, closed
assert closed[0]["close_reason"] == "TAKE_PROFIT", closed
assert closed[0]["pnl"] == 2.0, closed
assert closed[0]["r_multiple"] == 2.0, closed
assert closed[0]["telegram_sent"] is True, closed
assert texts, texts
assert "ИТОГ СДЕЛКИ" in texts[0], texts[0]

summary_text = runtime.build_daily_summary_text()
assert "ИТОГ ДНЯ ПО СИГНАЛАМ" in summary_text
assert "Всего сигналов: 1" in summary_text
assert "Закрыто сделок: 1" in summary_text

ok = runtime.send_daily_summary()
assert ok is True
assert len(texts) >= 2, texts
assert "ИТОГ ДНЯ ПО СИГНАЛАМ" in texts[-1], texts[-1]

print("SIGNAL_TRADE_RUNTIME_OK")
PY
