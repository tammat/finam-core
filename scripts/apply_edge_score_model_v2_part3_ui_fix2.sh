#!/usr/bin/env bash
set -euo pipefail

echo "=== APPLY_EDGE_SCORE_MODEL_V2_PART3_UI_FIX2 ==="

provider="src/marketcore/presentation/providers/max_edge_provider.py"
test -f "$provider"

python - <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/providers/max_edge_provider.py")
s = p.read_text(encoding="utf-8")

if "v2.edge_score_v2" not in s:
    s = s.replace(
        """                        edge_score,
                        confidence,""",
        """                        edge_score,
                        v2.edge_score_v2,
                        v2.economic_score,
                        v2.reliability_score,
                        v2.execution_score,
                        v2.risk_score,
                        rec.reconciliation_verdict,
                        rec.score_delta,
                        rec.rank_delta,
                        confidence,""",
        1,
    )

if "LEFT JOIN analytics.edge_score_model_v2 v2" not in s:
    s = s.replace(
        """                    FROM analytics.max_edge_ranking_v1
                    WHERE source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'""",
        """                    FROM analytics.max_edge_ranking_v1 r
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
                    WHERE r.source_version='MAX_EDGE_DISCOVERY_ENGINE_V1'""",
        1,
    )

# после alias r нужно квалифицировать старые поля
for col in [
    "rank_no", "candidate_id", "symbol", "strategy_code", "timeframe",
    "edge_score", "confidence", "expectancy", "profit_factor",
    "net_after_tax", "max_drawdown", "trades",
    "recommendation_code", "ranking_ts"
]:
    s = s.replace(f"                        {col},", f"                        r.{col},")
    s = s.replace(f"                    ORDER BY {col}", f"                    ORDER BY r.{col}")

s = s.replace("AND status='ACTIVE'", "AND r.status='ACTIVE'")
s = s.replace("ORDER BY ranking_ts DESC, rank_no ASC", "ORDER BY r.ranking_ts DESC, r.rank_no ASC")

p.write_text(s, encoding="utf-8")
print("patch_status=applied")
PY

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m py_compile "$provider"

echo "VERDICT=EDGE_SCORE_MODEL_V2_PART3_UI_FIX2_APPLIED"
