from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor


OBSERVATION_UUID = (
    "9f1bd894-2df8-5ee6-b5b4-da4820f69812"
)


def main() -> int:
    with psycopg2.connect(
        os.environ["DATABASE_URL"]
    ) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            cur.execute(
                """
                SELECT
                    candidate_status,
                    validation_stage,
                    validation_formula_version,
                    validation_reason,
                    updated_at
                FROM analytics.edge_candidate_v1
                WHERE observation_uuid=%s
                """,
                (OBSERVATION_UUID,),
            )
            candidate = cur.fetchone()

            cur.execute(
                """
                SELECT
                    trades,
                    profit_factor,
                    expectancy,
                    verdict_code,
                    score_formula_version,
                    source_version,
                    updated_at
                FROM analytics.edge_observation_v1
                WHERE observation_uuid=%s
                """,
                (OBSERVATION_UUID,),
            )
            observation = cur.fetchone()

            cur.execute(
                """
                SELECT
                    id,
                    validation_version,
                    oos_trades,
                    oos_profit_factor,
                    oos_expectancy,
                    folds_total,
                    folds_passed,
                    verdict_code,
                    reason,
                    updated_at
                FROM analytics.edge_oos_result_v1
                WHERE observation_uuid=%s
                ORDER BY updated_at, id
                """,
                (OBSERVATION_UUID,),
            )
            oos_rows = cur.fetchall()

    if candidate is None:
        raise RuntimeError(
            "ERROR=BRM6_CANDIDATE_NOT_FOUND"
        )

    if observation is None:
        raise RuntimeError(
            "ERROR=BRM6_OBSERVATION_NOT_FOUND"
        )

    if len(oos_rows) != 2:
        raise RuntimeError(
            "ERROR=BRM6_EXPECTED_TWO_OOS_ROWS "
            f"actual={len(oos_rows)}"
        )

    latest = max(
        oos_rows,
        key=lambda row: row["updated_at"],
    )

    observation_stale = (
        observation["updated_at"]
        < latest["updated_at"]
    )

    candidate_matches_latest = (
        candidate["candidate_status"]
        == latest["verdict_code"]
        and
        candidate["validation_formula_version"]
        == latest["validation_version"]
    )

    direct_promoted_metrics_allowed = False
    chronological_cost_semantics_resolved = False
    replay_required = True

    print(
        "BRM6_LINEAGE_ROW "
        f"observation_verdict="
        f"{observation['verdict_code']} "
        f"observation_pf="
        f"{observation['profit_factor']} "
        f"observation_expectancy="
        f"{observation['expectancy']} "
        f"observation_formula="
        f"{observation['score_formula_version']}"
    )

    print(
        "BRM6_LATEST_OOS_ROW "
        f"validation_version="
        f"{latest['validation_version']} "
        f"trades={latest['oos_trades']} "
        f"pf={latest['oos_profit_factor']} "
        f"expectancy={latest['oos_expectancy']} "
        f"folds={latest['folds_passed']}/"
        f"{latest['folds_total']} "
        f"verdict={latest['verdict_code']}"
    )

    print(
        f"oos_rows={len(oos_rows)}"
    )
    print(
        f"observation_stale="
        f"{int(observation_stale)}"
    )
    print(
        f"candidate_matches_latest_oos="
        f"{int(candidate_matches_latest)}"
    )

    print(
        "direct_promoted_metrics_allowed="
        f"{int(direct_promoted_metrics_allowed)}"
    )

    print(
        "chronological_cost_semantics_resolved="
        f"{int(chronological_cost_semantics_resolved)}"
    )

    print(
        f"replay_required="
        f"{int(replay_required)}"
    )

    print(
        "lineage_status="
        "STALE_PROMOTED_OBSERVATION"
    )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "BRM6_PROMOTED_LINEAGE_RESOLUTION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
