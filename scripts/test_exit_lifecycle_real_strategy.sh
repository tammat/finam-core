#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/exit_lifecycle_manager.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/execution/exit_lifecycle_manager.py").read_text(encoding="utf-8")

assert "lifecycle_strategy = p._strategy_name_for_symbol(symbol)" in text
assert 'strategy="default"' not in text
assert "strategy=lifecycle_strategy" in text
assert "PositionLifecycleService(p)" in text
assert '"strategy": lifecycle_strategy' in text
assert '"signal_id": f"exit-{symbol}-{int(time.time() * 1000)}"' in text

print("OK: ExitLifecycleManager uses real strategy key")
PY
