#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_UNIVERSE_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_universe_v1.py

src/scripts/research/build_research_universe_v1.py \
  | tee /tmp/research_universe_v1.out

grep -q "RESEARCH_UNIVERSE_V1" /tmp/research_universe_v1.out
grep -q "status=APPROVED_AFTER_ARCHITECTURE_FREEZE" /tmp/research_universe_v1.out
grep -q "INSTRUMENT class=FUTURES name=BRENT" /tmp/research_universe_v1.out
grep -q "INSTRUMENT class=FUTURES name=NATURAL_GAS" /tmp/research_universe_v1.out
grep -q "INSTRUMENT class=EQUITY ticker=SBER" /tmp/research_universe_v1.out
grep -q "CONTEXT code=IMOEX" /tmp/research_universe_v1.out
grep -q "SESSION code=MOSCOW_DAY" /tmp/research_universe_v1.out
grep -q "CALENDAR_EVENT code=EXPIRATION" /tmp/research_universe_v1.out
grep -q "rule=new_instruments_require_architectural_decision" /tmp/research_universe_v1.out
grep -q "VERDICT=RESEARCH_UNIVERSE_V1_READY" /tmp/research_universe_v1.out

echo "TEST_RESEARCH_UNIVERSE_V1_OK"
