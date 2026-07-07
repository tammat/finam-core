from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "SELF_LEARNING_RECOMMENDATION_ENGINE_V1"
OUT_TXT = Path("reports/self_learning_recommendation_latest.txt")
OUT_JSON = Path("reports/self_learning_recommendation_latest.json")


def d(value) -> Decimal:
    return Decimal(str(value or 0))


def decision(score: Decimal) -> str:
    if score >= Decimal("70"):
        return "ACTIVE"
    if score >= Decimal("40"):
        return "REVIEW"
    return "STOP"


def main() -> None:
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)

    rows_out = []

    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    recommendation_code,
                    count(*) AS feedback_rows,
                    count(*) FILTER (WHERE decision_outcome='SUCCESS') AS success_rows,
                    count(*) FILTER (WHERE decision_outcome='NO_EFFECT') AS no_effect_rows,
                    count(*) FILTER (WHERE decision_outcome='NEGATIVE_EFFECT') AS negative_rows,
                    coalesce(avg(confidence),0) AS avg_confidence
                FROM analytics.recommendation_feedback_v1
                GROUP BY recommendation_code
                ORDER BY recommendation_code;
            """)

            for row in cur.fetchall():
                feedback_rows = d(row["feedback_rows"])
                success_rows = d(row["success_rows"])
                negative_rows = d(row["negative_rows"])
                avg_conf = d(row["avg_confidence"])

                if feedback_rows <= 0:
                    score = Decimal("0")
                else:
                    success_component = success_rows / feedback_rows * Decimal("70")
                    penalty = negative_rows / feedback_rows * Decimal("40")
                    confidence_component = avg_conf * Decimal("0.30")
                    score = max(Decimal("0"), min(Decimal("100"), success_component + confidence_component - penalty))
                    score = score.quantize(Decimal("0.000001"))

                status = decision(score)

                cur.execute("""
                    INSERT INTO analytics.recommendation_score_v1 (
                        recommendation_code,
                        feedback_rows,
                        success_rows,
                        no_effect_rows,
                        negative_rows,
                        avg_confidence,
                        recommendation_score,
                        decision_status,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    row["recommendation_code"],
                    int(row["feedback_rows"]),
                    int(row["success_rows"]),
                    int(row["no_effect_rows"]),
                    int(row["negative_rows"]),
                    avg_conf,
                    score,
                    status,
                    SOURCE_VERSION,
                ))

                rows_out.append({
                    "recommendation_code": row["recommendation_code"],
                    "feedback_rows": int(row["feedback_rows"]),
                    "success_rows": int(row["success_rows"]),
                    "no_effect_rows": int(row["no_effect_rows"]),
                    "negative_rows": int(row["negative_rows"]),
                    "avg_confidence": float(avg_conf),
                    "recommendation_score": float(score),
                    "decision_status": status,
                })

            cur.execute("""
                SELECT count(*) AS unsafe_rows
                FROM analytics.edge_candidate_v1
                WHERE micro_live_allowed=true OR live_allowed=true;
            """)
            unsafe = int(cur.fetchone()["unsafe_rows"])

    payload = {
        "source_version": SOURCE_VERSION,
        "rows": rows_out,
        "unsafe_rows": unsafe,
        "verdict": "SELF_LEARNING_RECOMMENDATION_ENGINE_READY" if unsafe == 0 else "UNSAFE_ROWS_FOUND",
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "=== SELF_LEARNING_RECOMMENDATION_ENGINE_V1 ===",
        f"rows={len(rows_out)}",
        f"unsafe_rows={unsafe}",
    ]

    for row in rows_out:
        lines.append(
            "SCORE "
            f"recommendation={row['recommendation_code']} "
            f"score={row['recommendation_score']} "
            f"status={row['decision_status']} "
            f"feedback_rows={row['feedback_rows']}"
        )

    lines.append(f"VERDICT={payload['verdict']}")
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
