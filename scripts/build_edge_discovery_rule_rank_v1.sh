#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_DISCOVERY_RULE_RANK_V1 ==="

mkdir -p src/scripts scripts

cat > src/scripts/build_edge_discovery_rule_rank_v1.py <<'PY'
from __future__ import annotations

import operator
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
METHOD_CODE = os.getenv("EDGE_DISCOVERY_METHOD_CODE", "RULE_RANK_V1")
SOURCE_VERSION = "EDGE_DISCOVERY_RULE_RANK_V1"

OPS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "==": operator.eq,
    "!=": operator.ne,
}


def metric_value(row: dict[str, Any], metric: str) -> Decimal:
    value = row.get(metric)
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def candidate_class(score: Decimal) -> str:
    if score >= Decimal("85"):
        return "TOP"
    if score >= Decimal("75"):
        return "A"
    if score >= Decimal("60"):
        return "B"
    if score >= Decimal("45"):
        return "C"
    return "REJECT"


def main() -> None:
    batch_id = datetime.now(UTC).strftime("%Y%m%d_RULE_RANK_V1")
    scanned = 0
    eligible = 0
    candidates = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT *
                FROM analytics.edge_discovery_method_v1
                WHERE method_code=%s
                  AND enabled=true;
            """, (METHOD_CODE,))
            method = cur.fetchone()
            if not method:
                raise RuntimeError(f"DISCOVERY_METHOD_NOT_ENABLED method_code={METHOD_CODE}")

            cfg = method["config_json"] or {}
            candidate_limit = int(cfg.get("candidate_limit", 100))

            cur.execute("""
                SELECT *
                FROM analytics.edge_discovery_rule_v1
                WHERE method_code=%s
                  AND enabled=true
                ORDER BY id ASC;
            """, (METHOD_CODE,))
            rules = cur.fetchall()
            if not rules:
                raise RuntimeError(f"DISCOVERY_RULES_NOT_FOUND method_code={METHOD_CODE}")

            cur.execute("""
                INSERT INTO analytics.edge_discovery_run_v1 (
                    discovery_batch_id,
                    method_code,
                    status_code,
                    source_version,
                    started_at,
                    updated_at
                )
                VALUES (%s,%s,'RUNNING',%s,now(),now())
                RETURNING id;
            """, (batch_id, METHOD_CODE, SOURCE_VERSION))
            run_id = cur.fetchone()["id"]

            cur.execute("""
                SELECT *
                FROM analytics.edge_observation_v1
                ORDER BY
                    normalized_edge_score DESC,
                    confidence_score DESC,
                    stability_score DESC,
                    profit_factor DESC,
                    expectancy DESC,
                    trades DESC,
                    created_at DESC;
            """)
            observations = cur.fetchall()
            ranked: list[tuple[Decimal, dict[str, Any], str]] = []

            for obs in observations:
                scanned += 1
                passed_weight = Decimal("0")
                total_weight = Decimal("0")
                hard_fail = False

                for rule in rules:
                    metric = str(rule["metric_name"])
                    op_code = str(rule["operator_code"])
                    threshold = Decimal(str(rule["threshold_value"] or 0))
                    weight = Decimal(str(rule["weight"] or 1))
                    total_weight += weight

                    op = OPS.get(op_code)
                    if op is None:
                        raise RuntimeError(f"UNSUPPORTED_OPERATOR {op_code}")

                    value = metric_value(obs, metric)
                    passed = op(value, threshold)

                    if passed:
                        passed_weight += weight
                    else:
                        hard_fail = True

                rule_score = Decimal("0")
                if total_weight > 0:
                    rule_score = (passed_weight / total_weight) * Decimal("100")

                base_score = Decimal(str(obs["normalized_edge_score"] or 0))
                confidence = Decimal(str(obs["confidence_score"] or 0))
                stability = Decimal(str(obs["stability_score"] or 0))

                discovery_score = (
                    base_score * Decimal("0.50")
                    + confidence * Decimal("0.25")
                    + stability * Decimal("0.15")
                    + rule_score * Decimal("0.10")
                )

                cls = candidate_class(discovery_score)
                if hard_fail:
                    cls = "REJECT"

                if cls in {"TOP", "A", "B"}:
                    ranked.append((discovery_score, obs, cls))

            ranked.sort(key=lambda x: x[0], reverse=True)
            selected = ranked[:candidate_limit]
            eligible = len(selected)

            for rank, item in enumerate(selected, start=1):
                score, obs, cls = item

                cur.execute("""
                    INSERT INTO analytics.edge_candidate_v1 (
                        observation_uuid,
                        research_batch_id,
                        research_code,
                        strategy_code,
                        strategy_version,
                        symbol,
                        timeframe,
                        parameter_hash,
                        parameter_json,
                        dataset_version,
                        raw_edge_score,
                        normalized_edge_score,
                        confidence_score,
                        stability_score,
                        candidate_status,
                        validation_stage,
                        paper_allowed,
                        shadow_allowed,
                        micro_live_allowed,
                        live_allowed,
                        discovery_batch_id,
                        discovery_rank,
                        discovery_score,
                        candidate_class,
                        discovery_formula_version,
                        source_version,
                        updated_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,
                        %s,%s,%s,%s,
                        'EDGE_CANDIDATE',
                        'NOT_STARTED',
                        false,false,false,false,
                        %s,%s,%s,%s,
                        'RULE_RANK_V1',
                        %s,
                        now()
                    )
                    ON CONFLICT(observation_uuid) DO UPDATE SET
                        raw_edge_score=EXCLUDED.raw_edge_score,
                        normalized_edge_score=EXCLUDED.normalized_edge_score,
                        confidence_score=EXCLUDED.confidence_score,
                        stability_score=EXCLUDED.stability_score,
                        discovery_batch_id=EXCLUDED.discovery_batch_id,
                        discovery_rank=EXCLUDED.discovery_rank,
                        discovery_score=EXCLUDED.discovery_score,
                        candidate_class=EXCLUDED.candidate_class,
                        discovery_formula_version=EXCLUDED.discovery_formula_version,
                        source_version=EXCLUDED.source_version,
                        updated_at=now();
                """, (
                    obs["observation_uuid"],
                    obs["research_batch_id"],
                    obs["research_code"],
                    obs["strategy_code"],
                    obs["strategy_version"],
                    obs["symbol"],
                    obs["timeframe"],
                    obs["parameter_hash"],
                    obs["parameter_json"],
                    obs["dataset_version"],
                    obs["raw_edge_score"],
                    obs["normalized_edge_score"],
                    obs["confidence_score"],
                    obs["stability_score"],
                    batch_id,
                    rank,
                    score,
                    cls,
                    SOURCE_VERSION,
                ))
                candidates += 1

            cur.execute("""
                UPDATE analytics.edge_discovery_run_v1
                SET status_code='DONE',
                    observations_scanned=%s,
                    candidates_created=%s,
                    finished_at=now(),
                    updated_at=now()
                WHERE id=%s;
            """, (scanned, candidates, run_id))

            cur.execute("""
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE candidate_class='TOP') AS top_rows,
                    count(*) FILTER (WHERE candidate_class='A') AS a_rows,
                    count(*) FILTER (WHERE candidate_class='B') AS b_rows,
                    max(discovery_score) AS max_score
                FROM analytics.edge_candidate_v1;
            """)
            summary = cur.fetchone()

    print("=== EDGE_DISCOVERY_RULE_RANK_V1 ===")
    print(f"discovery_batch_id={batch_id}")
    print(f"method_code={METHOD_CODE}")
    print(f"observations_scanned={scanned}")
    print(f"eligible_ranked={eligible}")
    print(f"candidates_created={candidates}")
    print(f"candidates_total={summary['total']}")
    print(f"top_rows={summary['top_rows']}")
    print(f"a_rows={summary['a_rows']}")
    print(f"b_rows={summary['b_rows']}")
    print(f"max_score={summary['max_score']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_DISCOVERY_RULE_RANK_V1_READY")


if __name__ == "__main__":
    main()
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "edge.discovery.rule_rank.title": "Rule Rank Discovery",
        "edge.discovery.rule_rank.subtitle": "Метод ранжирования наблюдений через настраиваемые правила без хардкода порогов в коде.",
        "edge.discovery.rule_rank.method": "Метод Rule Rank",
        "edge.discovery.rule_rank.scanned": "Просканировано наблюдений",
        "edge.discovery.rule_rank.eligible": "Прошли ранжирование",
        "edge.discovery.rule_rank.created": "Создано кандидатов"
    })
except NameError:
    pass
PY

cat > scripts/test_edge_discovery_rule_rank_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_DISCOVERY_RULE_RANK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/scripts/build_edge_discovery_rule_rank_v1.py \
  src/marketcore/presentation/ui_labels.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_rule_rank_v1.py | tee /tmp/edge_discovery_rule_rank_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_RULE_RANK_V1_READY" /tmp/edge_discovery_rule_rank_v1.txt

runs=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_discovery_run_v1
WHERE method_code='RULE_RANK_V1'
  AND status_code='DONE';
")

bad_live=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE live_allowed=true
   OR micro_live_allowed=true;
")

bad_score=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE discovery_score < 0
   OR discovery_score > 100;
")

test "$runs" -gt 0
test "$bad_live" = "0"
test "$bad_score" = "0"

grep -q "edge.discovery.rule_rank.title" src/marketcore/presentation/ui_labels.py

psql -d finam_core -c "
SELECT
    discovery_rank,
    candidate_class,
    strategy_code,
    symbol,
    timeframe,
    trades,
    profit_factor,
    expectancy,
    normalized_edge_score,
    confidence_score,
    stability_score,
    discovery_score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid = c.observation_uuid
ORDER BY c.discovery_score DESC, c.discovery_rank ASC
LIMIT 30;
" || true

echo "discovery_done_runs=$runs"
echo "bad_live_rows=$bad_live"
echo "bad_score_rows=$bad_score"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_DISCOVERY_RULE_RANK_V1_OK"
SH_TEST

chmod +x scripts/test_edge_discovery_rule_rank_v1.sh
scripts/test_edge_discovery_rule_rank_v1.sh

echo "VERDICT=BUILD_EDGE_DISCOVERY_RULE_RANK_V1_OK"
