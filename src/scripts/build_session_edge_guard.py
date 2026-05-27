#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.session_edge_guard import SessionEdgeGuard


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--continuous-symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--trade-source", default="paper")

    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    sql = """
    SELECT
        session_bucket,
        hour_utc,
        hour_msk,
        closed_trades,
        expectancy,
        profit_factor,
        advisory_status,
        advisory_reason
    FROM session_edge_guard_v1
    WHERE continuous_symbol = %(continuous_symbol)s
      AND strategy = %(strategy)s
      AND timeframe = %(timeframe)s
      AND trade_source = %(trade_source)s
    ORDER BY hour_utc;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql,
                {
                    "continuous_symbol": args.continuous_symbol,
                    "strategy": args.strategy,
                    "timeframe": args.timeframe,
                    "trade_source": args.trade_source,
                },
            )
            rows = cur.fetchall()

    guard = SessionEdgeGuard(mode="soft_advisory")

    print(
        "SESSION_EDGE_GUARD_V1",
        f"rows={len(rows)}",
        f"mode=analytics_only",
        flush=True,
    )

    for r in rows:
        decision = guard.decide(
            session_bucket=r["session_bucket"],
            hour_utc=r["hour_utc"],
            advisory_status=r["advisory_status"],
            advisory_reason=r["advisory_reason"],
        )

        print(
            "SESSION_EDGE_ROW",
            f"session={r['session_bucket']}",
            f"hour_utc={r['hour_utc']}",
            f"hour_msk={r['hour_msk']}",
            f"closed={r['closed_trades']}",
            f"expectancy={r['expectancy']}",
            f"profit_factor={r['profit_factor']}",
            f"status={decision.status}",
            f"reason={decision.reason}",
            flush=True,
        )


if __name__ == "__main__":
    main()
