#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/trade_gate_service.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "trade_gate.cooldown_allows" in text
assert "trade_gate.trade_limit_allows" in text
assert "trade_gate.account_trade" in text
assert "PIPE_TRADE_LIMIT_ACCOUNTED" in text

# Старый inline-блок не должен остаться в основной ветке.
main_region = text[text.find("=== TRADE GATES: COOLDOWN + TRADE LIMIT"):text.find("=== PORTFOLIO KILL-SWITCH")]
assert "max_trades_per_hour = int(os.getenv" not in main_region
assert "self._last_trade_ts = now_ts" not in main_region
assert "self._trade_timestamps = trades" not in main_region

print("OK: pipeline delegates cooldown/trade-limit to TradeGateService")
PY
