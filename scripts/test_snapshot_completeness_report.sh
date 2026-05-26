#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/snapshot_completeness_report.py

python src/scripts/snapshot_completeness_report.py --help | grep -q -- "--symbols"
python src/scripts/snapshot_completeness_report.py --help | grep -q -- "--event-type"

echo "SNAPSHOT_COMPLETENESS_REPORT_COMPILE_OK"
