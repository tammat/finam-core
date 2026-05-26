#!/usr/bin/env python3

from __future__ import annotations

import os
import psycopg2

from finam_core.analytics.trade_outcome_quality_engine import TradeOutcomeQualityEngine


def dsn() -> str:
    return os.environ["DATABASE_URL"]


def main() -> None:
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:

            with open("sql/create_trade_outcome_quality_v1.sql", "r", encoding="utf-8") as f:
                cur.execute(f.read())

            cur.execute(
                """
                select
                    quality_grade,
                    regime_known,
                    partition_isolated
                from trade_outcome_quality_v1
                """
            )

            rows_raw = cur.fetchall()

            rows = [
                {
                    "quality_grade": r[0],
                    "regime_known": r[1],
                    "partition_isolated": r[2],
                }
                for r in rows_raw
            ]

            summary = TradeOutcomeQualityEngine.summarize(rows)

            print(
                "TRADE_OUTCOME_QUALITY_V1 "
                f"rows={summary['rows']} "
                f"A={summary['grades']['A']} "
                f"B={summary['grades']['B']} "
                f"C={summary['grades']['C']} "
                f"D={summary['grades']['D']} "
                f"regime_known_pct={summary['regime_known_pct']:.4f} "
                f"partition_isolated_pct={summary['partition_isolated_pct']:.4f}",
                flush=True,
            )


if __name__ == "__main__":
    main()
