#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_EDGE_SCORE_MODEL_V2_PART3_UI_FIX ==="

rm -rf src/scripts/__pycache__ src/marketcore/**/__pycache__ || true

provider="src/marketcore/presentation/providers/max_edge_provider.py"
test -f "$provider"

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/providers/max_edge_provider.py")
s = p.read_text(encoding="utf-8")

if "edge_score_v2" not in s:
    s = s.replace(
        "r.edge_score,",
        """r.edge_score,
                        v2.edge_score_v2,
                        v2.economic_score,
                        v2.reliability_score,
                        v2.execution_score,
                        v2.risk_score,
                        rec.reconciliation_verdict,
                        rec.score_delta,
                        rec.rank_delta,""",
        1,
    )

if "LEFT JOIN analytics.edge_score_model_v2 v2" not in s:
    marker = "WHERE r.source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'"
    join = """
                    LEFT JOIN analytics.edge_score_model_v2 v2
                      ON v2.symbol = r.symbol
                     AND v2.strategy_code = r.strategy_code
                     AND v2.timeframe = r.timeframe
                    LEFT JOIN LATERAL (
                        SELECT
                            rr.verdict AS reconciliation_verdict,
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
    if marker not in s:
        raise SystemExit("WHERE_MARKER_NOT_FOUND_IN_MAX_EDGE_PROVIDER")
    s = s.replace(marker, join + "                    " + marker, 1)

p.write_text(s, encoding="utf-8")
print("patch_status=applied")
PY

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile "$provider"

echo "VERDICT=EDGE_SCORE_MODEL_V2_PART3_UI_FIX_APPLIED"
