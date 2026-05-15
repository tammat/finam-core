#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/strategy_optimization_report.py

python src/scripts/strategy_optimization_report.py --dry-run \
| grep -E "ЛУЧШИЕ_СВЯЗКИ|ХУДШИЕ_СВЯЗКИ|PNL_ПО_ЧАСАМ|PNL_ПО_РЕЖИМАМ|КАНДИДАТЫ_НА_ОТКЛЮЧЕНИЕ|КАНДИДАТЫ_НА_УСИЛЕНИЕ" >/dev/null

echo "OK: отчёт оптимизации стратегий компилируется"
