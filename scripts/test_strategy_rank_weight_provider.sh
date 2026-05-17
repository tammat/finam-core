#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/strategy_rank_weight_provider.py

python - <<'PY'
from datetime import date
from decimal import Decimal

from finam_core.analytics.strategy_rank_weight_provider import StrategyRankWeightProvider


class FakeCursor:
    def __init__(self, decision):
        self.decision = decision

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        pass

    def fetchone(self):
        if self.decision is None:
            return None
        return (self.decision,)


class FakeConn:
    def __init__(self, decision):
        self.decision = decision

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return FakeCursor(self.decision)


class FakePg:
    def __init__(self, decision):
        self.decision = decision

    def _connect(self):
        return FakeConn(self.decision)


assert StrategyRankWeightProvider(FakePg("ENABLE")).get_weight(
    trade_date=date(2026, 5, 15),
    strategy="BR_CONSERVATIVE_BREAKOUT",
    symbol="BRM6@RTSX",
    timeframe="INTRADAY",
) == Decimal("1.00")

assert StrategyRankWeightProvider(FakePg("DISABLE")).get_weight(
    trade_date=date(2026, 5, 15),
    strategy="USDRUB_REGIME",
    symbol="USDRUBF@RTSX",
) == Decimal("0.00")

assert StrategyRankWeightProvider(FakePg(None)).get_weight(
    trade_date=date(2026, 5, 15),
    strategy="NEW",
    symbol="SBER@MISX",
) == Decimal("0.25")

print("OK: strategy rank weight provider")
PY
