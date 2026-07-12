from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from scripts.build_edge_score_engine_v2 import SCORE_FORMULA_VERSION, score_row


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_ID = os.getenv("RESEARCH_BATCH_ID", "20260712_MOMENTUM_THRESHOLD_RECALC_V2")
SOURCE_VERSION = "MOMENTUM_THRESHOLD_RECALC_SCORE_V2"


def main() -> None:
    updated = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM analytics.edge_observation_v1 WHERE research_batch_id=%s ORDER BY id",
                (BATCH_ID,),
            )
            rows = cur.fetchall()
            if not rows:
                raise RuntimeError(f"RECALCULATION_BATCH_EMPTY batch_id={BATCH_ID}")

            for row in rows:
                scores = score_row(row)
                cur.execute(
                    """
                    UPDATE analytics.edge_observation_v1
                    SET raw_edge_score=%s,normalized_edge_score=%s,
                        confidence_score=%s,stability_score=%s,research_cost_score=%s,
                        score_formula_version=%s,source_version=%s,updated_at=now()
                    WHERE id=%s
                    """,
                    (
                        scores["raw_edge_score"],
                        scores["normalized_edge_score"],
                        scores["confidence_score"],
                        scores["stability_score"],
                        scores["research_cost_score"],
                        SCORE_FORMULA_VERSION,
                        SOURCE_VERSION,
                        row["id"],
                    ),
                )
                updated += 1

    print(f"research_batch_id={BATCH_ID}")
    print(f"scored={updated}")
    print("historical_observations_changed=0")
    print("VERDICT=SCORE_MOMENTUM_EDGE_RECALCULATION_V2_OK")


if __name__ == "__main__":
    main()
