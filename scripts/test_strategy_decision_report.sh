#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/strategy_decision_report.py

python src/scripts/strategy_decision_report.py --dry-run \
| grep -E "РЕШЕНИЯ_ПО_СТРАТЕГИЯМ|УСИЛИТЬ|ОТКЛЮЧИТЬ|ТОЛЬКО_НАБЛЮДАТЬ|ДОЛГ_ПО_ДАННЫМ" >/dev/null

echo "OK: отчёт решений по стратегиям компилируется"
