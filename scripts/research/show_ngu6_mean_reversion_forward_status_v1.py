#!/usr/bin/env python3
from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    CANDIDATE_CODE,
    FORWARD_BOUNDARY,
    FREEZE_COMMIT,
    FREEZE_SHA256,
    SYMBOL,
    TIMEFRAME,
)


TABLE = "analytics.ngu6_mr_forward_observation_v1"


def main() -> int:
    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT
                    max(ts) AS latest_bar,
                    count(*) FILTER (
                        WHERE ts > %s
                    )::bigint AS forward_bars
                FROM public.market_bars
                WHERE symbol = %s
                  AND timeframe = %s
                """,
                (
                    FORWARD_BOUNDARY,
                    SYMBOL,
                    TIMEFRAME,
                ),
            )

            market = cur.fetchone()

            cur.execute(
                f"""
                SELECT
                    count(*)::bigint AS total,
                    count(*) FILTER (
                        WHERE observation_status='OPEN'
                    )::bigint AS open_count,
                    count(*) FILTER (
                        WHERE observation_status='CLOSED'
                    )::bigint AS closed_count,
                    count(*) FILTER (
                        WHERE observation_status='CLOSED'
                          AND net_pnl > 0
                    )::bigint AS wins,
                    count(*) FILTER (
                        WHERE observation_status='CLOSED'
                          AND net_pnl < 0
                    )::bigint AS losses,
                    coalesce(
                        sum(net_pnl) FILTER (
                            WHERE observation_status='CLOSED'
                        ),
                        0
                    ) AS net_pnl,
                    avg(net_pnl) FILTER (
                        WHERE observation_status='CLOSED'
                    ) AS expectancy,
                    sum(net_pnl) FILTER (
                        WHERE observation_status='CLOSED'
                          AND net_pnl > 0
                    ) AS gross_wins,
                    -sum(net_pnl) FILTER (
                        WHERE observation_status='CLOSED'
                          AND net_pnl < 0
                    ) AS gross_losses,
                    count(*) FILTER (
                        WHERE NOT shadow_only
                           OR broker_order_sent
                           OR runtime_allowed
                           OR execution_enabled
                    )::bigint AS unsafe_count,
                    count(*) FILTER (
                        WHERE candidate_code <> %s
                           OR freeze_commit <> %s
                           OR freeze_sha256 <> %s
                           OR symbol <> %s
                           OR timeframe <> %s
                    )::bigint AS lineage_mismatch
                FROM {TABLE}
                """,
                (
                    CANDIDATE_CODE,
                    FREEZE_COMMIT,
                    FREEZE_SHA256,
                    SYMBOL,
                    TIMEFRAME,
                ),
            )

            status = cur.fetchone()

            cur.execute(
                f"""
                SELECT
                    signal_ts,
                    side,
                    observation_status,
                    exit_ts,
                    net_pnl,
                    ac100,
                    contract_spec_id,
                    contract_multiplier
                FROM {TABLE}
                WHERE candidate_code = %s
                ORDER BY signal_ts DESC
                LIMIT 10
                """,
                (CANDIDATE_CODE,),
            )

            latest = cur.fetchall()

    gross_wins = status["gross_wins"]
    gross_losses = status["gross_losses"]

    if (
        gross_losses is None
        or gross_losses == 0
    ):
        profit_factor = None
    else:
        profit_factor = (
            (gross_wins or 0)
            / gross_losses
        )

    print("=== NGU6 FORWARD STATUS V1 ===")
    print(f"candidate={CANDIDATE_CODE}")
    print(f"freeze_commit={FREEZE_COMMIT}")
    print(f"boundary={FORWARD_BOUNDARY.isoformat()}")
    print(f"latest_bar={market['latest_bar']}")
    print(f"forward_bars={market['forward_bars']}")
    print(f"total={status['total']}")
    print(f"open={status['open_count']}")
    print(f"closed={status['closed_count']}")
    print(f"wins={status['wins']}")
    print(f"losses={status['losses']}")
    print(f"net_pnl={status['net_pnl']}")
    print(f"expectancy={status['expectancy']}")
    print(
        "profit_factor="
        f"{profit_factor if profit_factor is not None else 'NONE'}"
    )
    print(f"unsafe={status['unsafe_count']}")
    print(
        f"lineage_mismatch="
        f"{status['lineage_mismatch']}"
    )

    print()
    print("=== LATEST OBSERVATIONS ===")

    if not latest:
        print("NONE")
    else:
        for row in latest:
            print(
                f"signal_ts={row['signal_ts']} "
                f"side={row['side']} "
                f"status={row['observation_status']} "
                f"exit_ts={row['exit_ts']} "
                f"net_pnl={row['net_pnl']} "
                f"ac100={row['ac100']} "
                f"contract_spec_id="
                f"{row['contract_spec_id']} "
                f"multiplier="
                f"{row['contract_multiplier']}"
            )

    if status["unsafe_count"] != 0:
        raise SystemExit(
            "ERROR=UNSAFE_FORWARD_OBSERVATION"
        )

    if status["lineage_mismatch"] != 0:
        raise SystemExit(
            "ERROR=FORWARD_LINEAGE_MISMATCH"
        )

    print()
    print("DATABASE_WRITE=NO")
    print("paper_allowed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "NGU6_FORWARD_STATUS_READONLY_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
