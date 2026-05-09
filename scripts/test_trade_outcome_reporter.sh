#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.analytics.trade_outcome_reporter import TradeOutcomeReporter

messages = []

class FakeNotifier:
    def send(self, text):
        messages.append(text)

reporter = TradeOutcomeReporter(FakeNotifier())

outcome = reporter.analyze(
    symbol="BRN6@RTSX",
    side="BUY",
    entry_price=80.0,
    exit_price=82.0,
    qty=1,
    stop_loss=79.0,
    take_profit=82.0,
    reason="цель достигнута",
)

assert outcome.result == "PROFIT"
assert "fees=1.75" in outcome.reason
assert "net_pnl=1998.25" in outcome.reason, outcome
assert outcome.pnl == 2000.0, outcome
assert outcome.rr_planned == 2.0, outcome
assert outcome.r_multiple == 2.0, outcome

ok = reporter.send_outcome(outcome)

assert ok is True
assert messages
assert "ИТОГ СДЕЛКИ" in messages[0]
assert "P&L" in messages[0]
assert "2.00R" in messages[0]

loss = reporter.analyze(
    symbol="NGQ6@RTSX",
    side="SELL",
    entry_price=3.50,
    exit_price=3.60,
    qty=10,
    stop_loss=3.60,
    take_profit=3.30,
    reason="стоп-лосс",
)

assert loss.result == "LOSS", loss
assert loss.pnl < 0, loss
assert loss.r_multiple == -1.0, loss

print("TRADE_OUTCOME_REPORTER_OK")
PY
