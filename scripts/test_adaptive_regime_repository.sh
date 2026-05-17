#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/risk/adaptive_regime_filter.py \
  src/finam_core/risk/adaptive_regime_repository.py

python - <<'PY'
from finam_core.risk.adaptive_regime_filter import AdaptiveRegimeFilter
from finam_core.risk.adaptive_regime_repository import AdaptiveRegimeRepository


class Cursor:
    def execute(self, sql, params):
        assert params[0] == "⚪ Обычная активность"

    def fetchone(self):
        return ("⚪ Обычная активность", 20, -50.0, 30.0)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Conn:
    def cursor(self):
        return Cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class PgLogger:
    def _connect(self):
        return Conn()


repo = AdaptiveRegimeRepository(
    PgLogger(),
    AdaptiveRegimeFilter(
        min_closed_trades=5,
        block_net_pnl_below=-10,
        reduce_net_pnl_below=0,
    ),
)

decision = repo.evaluate_regime("⚪ Обычная активность")

assert decision.allowed is False
assert decision.action == "BLOCK"
assert decision.multiplier == 0.0
assert "режим_убыточен" in decision.reason

print("OK: AdaptiveRegimeRepository")
PY
