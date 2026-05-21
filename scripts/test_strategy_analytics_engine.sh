#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/strategy_analytics_engine.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/strategy_analytics_engine.py").read_text(encoding="utf-8")

checks = [
    "pnl_by_execution_symbol.tsv",
    "exposure_by_adaptive_multiplier.tsv",
    "execution_lineage.tsv",
    "institutional_flow_latest.tsv",
    "opportunity_latest.tsv",
    "strategy_signal_quality_proxy.tsv",
    "institutional_flow_regime_events",
    "market_opportunity_metrics",
    "adaptive_position_multiplier",
    "Обычная активность",
    "Приоритет покупок",
    "Кандидат крупного потока",
    "Контекст крупного потока",
]

for c in checks:
    assert c in text, c

print("OK: Strategy analytics engine static check")
PY

PYTHONPATH=src python src/scripts/strategy_analytics_engine.py

test -f reports/strategy_analytics/pnl_by_execution_symbol.tsv
test -f reports/strategy_analytics/exposure_by_adaptive_multiplier.tsv
test -f reports/strategy_analytics/execution_lineage.tsv
test -f reports/strategy_analytics/institutional_flow_latest.tsv
test -f reports/strategy_analytics/opportunity_latest.tsv
test -f reports/strategy_analytics/strategy_signal_quality_proxy.tsv

echo "OK: Strategy analytics engine"
