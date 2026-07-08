#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_EDGE_SCORE_MODEL_V2_PART4B_MAX_EDGE_EXPLAIN_UI ==="

provider="src/marketcore/presentation/providers/max_edge_provider.py"
test -f "$provider"

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/providers/max_edge_provider.py")
s = p.read_text(encoding="utf-8")

if "edge_score_explain_groups" in s:
    print("patch_status=already_applied")
    raise SystemExit(0)

# Добавляем LATERAL JSON explain по группам.
join_anchor = ") rec ON true"
join_block = """
                    LEFT JOIN LATERAL (
                        SELECT
                            COALESCE(
                                jsonb_agg(
                                    jsonb_build_object(
                                        'group_code', e.group_code,
                                        'group_score', e.group_score,
                                        'group_weight', e.group_weight,
                                        'group_contribution', e.group_contribution,
                                        'edge_score_v2', e.edge_score_v2,
                                        'model_verdict', e.model_verdict
                                    )
                                    ORDER BY e.group_code
                                ),
                                '[]'::jsonb
                            ) AS edge_score_explain_groups
                        FROM analytics.edge_score_model_v2_explain e
                        WHERE e.symbol = r.symbol
                          AND e.strategy_code = r.strategy_code
                          AND e.timeframe = r.timeframe
                          AND e.source_version = 'EDGE_SCORE_MODEL_V2_PART_4_EXPLAIN_CARD'
                    ) explain ON true
"""

if join_anchor not in s:
    raise SystemExit("REC_JOIN_ANCHOR_NOT_FOUND")

s = s.replace(join_anchor, join_anchor + join_block, 1)

select_anchor = "rec.rank_delta,"
if select_anchor not in s:
    raise SystemExit("SELECT_REC_RANK_DELTA_ANCHOR_NOT_FOUND")

s = s.replace(
    select_anchor,
    """rec.rank_delta,
                        explain.edge_score_explain_groups,""",
    1,
)

p.write_text(s, encoding="utf-8")
print("patch_status=applied")
PY

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile "$provider"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_PART4B_MAX_EDGE_EXPLAIN_UI_PATCH_READY"
