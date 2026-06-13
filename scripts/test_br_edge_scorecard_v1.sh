#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PY_BIN="${PY_BIN:-/opt/finam-core/venv/bin/python}"
[[ -x "$PY_BIN" ]] || PY_BIN="$(command -v python3)"

echo "TEST_BR_EDGE_SCORECARD_V1_START"

"$PY_BIN" -m py_compile src/scripts/analytics/build_br_edge_scorecard_v1.py

set +e
SYMBOL=BRM6@RTSX STRATEGY=BR_CONSERVATIVE_BREAKOUT \
  "$PY_BIN" src/scripts/analytics/build_br_edge_scorecard_v1.py \
  > /tmp/br_edge_scorecard_v1.out
rc=$?
set -e

grep -q "BR EDGE SCORECARD V1" /tmp/br_edge_scorecard_v1.out
grep -q "SOURCE REPORTS" /tmp/br_edge_scorecard_v1.out
grep -q "EDGE STATUS" /tmp/br_edge_scorecard_v1.out
grep -q "FINAL VERDICT" /tmp/br_edge_scorecard_v1.out

if [[ "$rc" != "0" && "$rc" != "2" ]]; then
  echo "UNEXPECTED_EXIT_CODE=$rc"
  cat /tmp/br_edge_scorecard_v1.out
  exit 1
fi

echo "TEST_BR_EDGE_SCORECARD_V1_OK"
