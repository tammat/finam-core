#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_SCORE_ENGINE_V2 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_edge_score_engine_v2.py <<'PY'
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("EDGE_SCORE_ENGINE_LIMIT", "5000"))
SOURCE_VERSION = "EDGE_SCORE_ENGINE_V2"
SCORE_FORMULA_VERSION = "EDGE_SCORE_FORMULA_V2"


def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def score_row(r: dict) -> dict:
    trades = float(r["trades"] or 0)
    pf = float(r["profit_factor"] or 0)
    expectancy = float(r["expectancy"] or 0)
    win_rate = float(r["win_rate"] or 0)
    recovery = float(r["recovery_factor"] or 0)
    drawdown = abs(float(r["max_drawdown"] or 0))
    cost = float(r["research_elapsed_ms"] or 0)

    trade_score = clamp((trades / 100.0) * 100.0)
    pf_score = clamp((pf - 1.0) * 100.0)
    expectancy_score = clamp(50.0 + expectancy * 100.0)
    win_score = clamp(win_rate * 100.0)
    recovery_score = clamp(recovery * 25.0)
    drawdown_penalty = clamp(drawdown * 10.0)
    cost_penalty = clamp(cost / 1000.0)

    raw = (
        0.30 * pf_score
        + 0.25 * expectancy_score
        + 0.15 * win_score
        + 0.15 * recovery_score
        + 0.15 * trade_score
        - 0.10 * drawdown_penalty
        - 0.05 * cost_penalty
    )

    normalized = clamp(raw)
    confidence = clamp(20.0 + trade_score * 0.8)
    stability = clamp(50.0 + recovery_score - drawdown_penalty)
    research_cost_score = clamp(100.0 - cost_penalty)

    return {
        "raw_edge_score": round(raw, 6),
        "normalized_edge_score": round(normalized, 6),
        "confidence_score": round(confidence, 6),
        "stability_score": round(stability, 6),
        "research_cost_score": round(research_cost_score, 6),
    }


def main() -> None:
    updated = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM analytics.edge_observation_v1
                ORDER BY created_at DESC, id DESC
                LIMIT %s;
            """, (LIMIT,))
            rows = cur.fetchall()

            for r in rows:
                scores = score_row(r)

                cur.execute("""
                    UPDATE analytics.edge_observation_v1
                    SET
                        raw_edge_score=%s,
                        normalized_edge_score=%s,
                        confidence_score=%s,
                        stability_score=%s,
                        research_cost_score=%s,
                        score_formula_version=%s,
                        source_version=%s,
                        updated_at=now()
                    WHERE id=%s;
                """, (
                    scores["raw_edge_score"],
                    scores["normalized_edge_score"],
                    scores["confidence_score"],
                    scores["stability_score"],
                    scores["research_cost_score"],
                    SCORE_FORMULA_VERSION,
                    SOURCE_VERSION,
                    r["id"],
                ))
                updated += 1

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE trades > 0) AS with_trades,
                    count(*) FILTER (WHERE normalized_edge_score >= 60) AS strong_rows,
                    avg(normalized_edge_score) AS avg_score,
                    max(normalized_edge_score) AS max_score
                FROM analytics.edge_observation_v1;
            """)
            s = cur.fetchone()

    print("=== EDGE_SCORE_ENGINE_V2 ===")
    print(f"scored_rows={updated}")
    print(f"observations_total={s['total']}")
    print(f"observations_with_trades={s['with_trades']}")
    print(f"strong_rows={s['strong_rows']}")
    print(f"avg_score={s['avg_score']}")
    print(f"max_score={s['max_score']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_SCORE_ENGINE_V2_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.score.engine.title": "Edge Score Engine",
        "edge.score.engine.subtitle": "Оценка исследовательских наблюдений без принятия решений о кандидатах.",
        "edge.score.raw": "Raw Score",
        "edge.score.normalized": "Normalized Score",
        "edge.score.confidence": "Confidence",
        "edge.score.stability": "Stability",
        "edge.score.research_cost": "Research Cost"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_score_engine_v2.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_ENGINE_V2 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_score_engine_v2.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core EDGE_SCORE_ENGINE_LIMIT=5000 PYTHONPATH=src \
python src/scripts/build_edge_score_engine_v2.py | tee /tmp/edge_score_engine_v2.txt

grep -q "VERDICT=EDGE_SCORE_ENGINE_V2_READY" /tmp/edge_score_engine_v2.txt

obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
scored=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_observation_v1
WHERE score_formula_version='EDGE_SCORE_FORMULA_V2';
")
bad=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_observation_v1
WHERE normalized_edge_score < 0
   OR normalized_edge_score > 100
   OR confidence_score < 0
   OR confidence_score > 100
   OR stability_score < 0
   OR stability_score > 100;
")

test "$obs" -gt 0
test "$scored" -gt 0
test "$bad" = "0"

grep -q "edge.score.engine.title" src/marketcore/presentation/ui_labels.py

echo "observations=$obs"
echo "scored_rows=$scored"
echo "bad_score_rows=$bad"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SCORE_ENGINE_V2_OK"
SH_TEST

chmod +x scripts/test_edge_score_engine_v2.sh
scripts/test_edge_score_engine_v2.sh

echo "VERDICT=BUILD_EDGE_SCORE_ENGINE_V2_OK"
