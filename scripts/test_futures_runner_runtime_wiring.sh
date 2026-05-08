#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_finam_futures_signal_radar.py").read_text()

assert "SignalTradeRuntime" in text
assert "runtime = SignalTradeRuntime(notifier)" in text
assert "runtime.register_signal" in text
assert "runtime.on_quote" in text
assert "runtime.send_daily_summary" in text

print("FUTURES_RUNNER_RUNTIME_WIRING_OK")
PY
