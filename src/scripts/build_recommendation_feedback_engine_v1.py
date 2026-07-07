from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "RECOMMENDATION_FEEDBACK_ENGINE_V1"
OUT_JSON = Path("reports/recommendation_feedback_latest.json")
OUT_TXT = Path("reports/recommendation_feedback_latest.txt")


def json_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def scalar(cur, sql: str) -> Decimal:
    cur.execute(sql)
    row = cur.fetchone()
    if not row:
        return Decimal("0")
    return Decimal(str(list(row.values())[0] or 0))


def outcome(delta: Decimal) -> str:
    if delta > Decimal("0"):
        return "SUCCESS"
    if delta == Decimal("0"):
        return "NO_EFFECT"
    return "NEGATIVE_EFFECT"


def confidence(delta: Decimal, baseline: Decimal) -> Decimal:
    if baseline <= 0:
        return Decimal("0")
    value = abs(delta / baseline * Decimal("100"))
    return min(value, Decimal("100")).quantize(Decimal("0.000001"))


def insert_feedback(cur, recommendation_code: str, metric: str, baseline: Decimal, current: Decimal) -> dict:
    delta = current - baseline
    improved = delta > 0
    conf = confidence(delta, baseline)
    result = outcome(delta)

    cur.execute(
        """
        INSERT INTO analytics.recommendation_feedback_v1 (
            recommendation_code,
            target_metric,
            baseline_value,
            current_value,
            delta_value,
            improved,
            confidence,
            decision_outcome,
            status,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            recommendation_code,
            metric,
            baseline,
            current,
            delta,
            improved,
            conf,
            result,
            "ACTIVE",
            SOURCE_VERSION,
        ),
    )

    return {
        "recommendation_code": recommendation_code,
        "target_metric": metric,
        "baseline_value": baseline,
        "current_value": current,
        "delta_value": delta,
        "improved": improved,
        "confidence": conf,
        "decision_outcome": result,
    }


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    feedback_rows = []

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            candidates_now = scalar(cur, "SELECT count(*) FROM analytics.edge_candidate_v1")
            paper_now = scalar(cur, "SELECT count(*) FROM analytics.paper_runtime_candidate_v1 WHERE paper_status='ACTIVE'")
            observations_now = scalar(cur, "SELECT count(*) FROM analytics.edge_observation_v1")

            cur.execute("""
                SELECT
                    recommendation_code,
                    target_metric,
                    current_value
                FROM analytics.recommendation_feedback_v1
                WHERE id IN (
                    SELECT max(id)
                    FROM analytics.recommendation_feedback_v1
                    GROUP BY recommendation_code, target_metric
                );
            """)
            previous = {
                (row["recommendation_code"], row["target_metric"]): Decimal(str(row["current_value"]))
                for row in cur.fetchall()
            }

            feedback_rows.append(insert_feedback(
                cur,
                "EXPAND_PARAMETERS",
                "CANDIDATE_COUNT",
                previous.get(("EXPAND_PARAMETERS", "CANDIDATE_COUNT"), candidates_now),
                candidates_now,
            ))

            feedback_rows.append(insert_feedback(
                cur,
                "PAPER_REPRICE",
                "PAPER_ACTIVE_COUNT",
                previous.get(("PAPER_REPRICE", "PAPER_ACTIVE_COUNT"), paper_now),
                paper_now,
            ))

            feedback_rows.append(insert_feedback(
                cur,
                "COLLECT_MORE_DATA",
                "OBSERVATION_COUNT",
                previous.get(("COLLECT_MORE_DATA", "OBSERVATION_COUNT"), observations_now),
                observations_now,
            ))

            unsafe = scalar(cur, "SELECT count(*) FROM analytics.edge_candidate_v1 WHERE micro_live_allowed=true OR live_allowed=true")

    payload = {
        "source_version": SOURCE_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "feedback": feedback_rows,
        "unsafe_rows": unsafe,
        "verdict": "RECOMMENDATION_FEEDBACK_ENGINE_READY" if unsafe == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")

    lines = [
        "=== RECOMMENDATION_FEEDBACK_ENGINE_V1 ===",
        f"generated_at={payload['generated_at']}",
        f"feedback_rows={len(feedback_rows)}",
        f"unsafe_rows={unsafe}",
    ]

    for row in feedback_rows:
        lines.append(
            "FEEDBACK "
            f"recommendation={row['recommendation_code']} "
            f"metric={row['target_metric']} "
            f"baseline={row['baseline_value']} "
            f"current={row['current_value']} "
            f"delta={row['delta_value']} "
            f"outcome={row['decision_outcome']}"
        )

    lines.append(f"VERDICT={payload['verdict']}")

    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
