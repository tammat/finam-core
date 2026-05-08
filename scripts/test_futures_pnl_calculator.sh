#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export FUTURES_POINT_VALUE_BR=1000
export FUTURES_POINT_VALUE_NG=100

python - <<'PY'
from finam_core.analytics.futures_pnl import FuturesPnlCalculator
from finam_core.analytics.trade_outcome_reporter import TradeOutcomeReporter

class FakeNotifier:
    def send(self, text):
        pass

calc = FuturesPnlCalculator()

assert calc.pnl(symbol="BRM6@RTSX", side="BUY", entry=80, exit=82, qty=1) == 2000.0
assert calc.pnl(symbol="BRM6@RTSX", side="SELL", entry=80, exit=78, qty=2) == 4000.0
assert calc.pnl(symbol="NGK6@RTSX", side="BUY", entry=3.0, exit=3.1, qty=3) == 30.0

reporter = TradeOutcomeReporter(FakeNotifier())

outcome = reporter.analyze(
    symbol="BRM6@RTSX",
    side="BUY",
    entry_price=80,
    exit_price=82,
    qty=1,
    stop_loss=79,
    take_profit=82,
    reason="test",
)

assert outcome.pnl == 2000.0, outcome
assert outcome.r_multiple == 2.0, outcome

print("FUTURES_PNL_CALCULATOR_OK")
PY
