#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_EDGE_SCORE_MODEL_V2_PART3_UI_PATCH ==="

target=$(grep -RIl "max_edge_ranking_v1" src/marketcore/presentation src/scripts | head -1)

if [ -z "${target:-}" ]; then
  echo "MAX_EDGE_UI_SOURCE_NOT_FOUND"
  exit 1
fi

echo "target=$target"

python - "$target" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")

if "edge_score_v2" in s and "reconciliation_verdict" in s:
    print("patch_status=already_applied")
    raise SystemExit(0)

# 1. Добавляем поля в SELECT рядом с основным score/rank.
select_marker = "r.edge_score"
if select_marker not in s:
    select_marker = "edge_score"

if select_marker not in s:
    print("SELECT_MARKER_NOT_FOUND")
    raise SystemExit(1)

s = s.replace(
    select_marker,
    """r.edge_score,
        v2.edge_score_v2,
        v2.group_economic_score,
        v2.group_reliability_score,
        v2.group_execution_score,
        v2.group_risk_score,
        rec.reconciliation_verdict,
        rec.score_delta,
        rec.rank_delta""",
    1,
)

# 2. Добавляем LEFT JOIN после FROM/JOIN max_edge_ranking_v1 alias r.
join_block = """
LEFT JOIN analytics.edge_score_model_v2 v2
  ON v2.symbol = r.symbol
 AND v2.strategy_code = r.strategy_code
 AND v2.timeframe = r.timeframe

LEFT JOIN LATERAL (
    SELECT rr.verdict AS reconciliation_verdict,
           rr.score_delta,
           rr.rank_delta
    FROM analytics.edge_score_model_v2_reconciliation rr
    WHERE rr.symbol = r.symbol
      AND rr.strategy_code = r.strategy_code
      AND rr.timeframe = r.timeframe
    ORDER BY rr.check_ts DESC
    LIMIT 1
) rec ON true
"""

markers = [
    "WHERE r.status",
    "WHERE status",
    "ORDER BY",
]

for marker in markers:
    if marker in s:
        s = s.replace(marker, join_block + "\n" + marker, 1)
        break
else:
    print("JOIN_INSERT_MARKER_NOT_FOUND")
    raise SystemExit(1)

# 3. Минимально добавляем вывод ключей, если UI формирует HTML руками.
if "reconciliation_verdict" not in s:
    print("PATCH_INTERNAL_ERROR")
    raise SystemExit(1)

p.write_text(s, encoding="utf-8")
print("patch_status=applied")
PY

echo "VERDICT=EDGE_SCORE_MODEL_V2_PART3_UI_PATCH_APPLIED"
