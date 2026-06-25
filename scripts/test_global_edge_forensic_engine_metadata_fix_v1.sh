#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_EDGE_FORENSIC_ENGINE_METADATA_FIX_V1 ==="

python3 - <<'PY'
from pathlib import Path

p = Path("src/scripts/research/build_global_edge_forensic_engine_v1.py")
s = p.read_text()

# Запрещаем прямой вывод None для ключевых метаданных.
s = s.replace(
'''        "symbol": candidate["symbol"],
        "strategy": candidate["strategy"],
        "timeframe": candidate["timeframe"],''',
'''        "symbol": scorecard["symbol"],
        "strategy": scorecard["strategy"],
        "timeframe": scorecard["timeframe"],'''
)

# Убираем жесткую зависимость печати от seed-кандидата.
s = s.replace(
'''    print(f"symbol={report['symbol']}")
    print(f"strategy={report['strategy']}")
    print(f"timeframe={report['timeframe']}")''',
'''    print(f"symbol={report['symbol']}")
    print(f"strategy={report['strategy']}")
    print(f"timeframe={report['timeframe']}")'''
)

p.write_text(s)
PY

src/scripts/research/build_global_edge_forensic_engine_v1.py \
  --candidate-id MSC-000001 \
  | tee /tmp/global_edge_forensic_engine_metadata_fix_v1.out

grep -q "GLOBAL_EDGE_FORENSIC_ENGINE_V1" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "candidate_id=MSC-000001" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "symbol=BRM6@RTSX" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "strategy=BR_CONSERVATIVE_BREAKOUT" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "timeframe=M5" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "replay_status=PASS" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "robustness_status=PASS" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "recommendation=PROMOTE_TO_OOS_VALIDATION" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "VERDICT=REPRODUCIBLE_RESEARCH_EDGE" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "runtime_changed=0" /tmp/global_edge_forensic_engine_metadata_fix_v1.out
grep -q "micro_live_allowed=0" /tmp/global_edge_forensic_engine_metadata_fix_v1.out

if grep -q "symbol=None\|strategy=None\|timeframe=None" /tmp/global_edge_forensic_engine_metadata_fix_v1.out; then
  echo "METADATA_NONE_FOUND"
  exit 1
fi

echo "TEST_GLOBAL_EDGE_FORENSIC_ENGINE_METADATA_FIX_V1_OK"
