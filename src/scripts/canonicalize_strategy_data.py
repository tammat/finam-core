from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.strategy_canonicalizer import (
    canonicalize_strategy_name,
    canonicalize_timeframe,
)


TABLES = [
    "trades",
    "closed_trade_chains_v2",
    "trade_attribution_v2",
    "trade_context_snapshots",
    "strategy_statistics_v2",
    "strategy_ranking_v2",
    "strategy_promotion_runtime_feed",
    "runtime_strategy_selection",
    "strategy_lifecycle_state",
    "strategy_promotion_decisions",
    "strategy_exit_alpha_policy",
    "strategy_exit_alpha_replay",
]


def columns_for(cur, table: str) -> set[str]:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name=%s
    """, (table,))
    return {row[0] for row in cur.fetchall()}


def normalize_table(
    cur,
    *,
    table: str,
    symbols: list[str],
) -> int:
    cols = columns_for(cur, table)

    if "id" not in cols or "strategy" not in cols:
        return 0

    where = ""
    params: list[object] = []

    if "symbol" in cols and symbols:
        where = "WHERE symbol = ANY(%s)"
        params.append(symbols)

    cur.execute(
        f"""
        SELECT id, strategy, timeframe
        FROM {table}
        {where}
        """,
        params,
    )

    rows = cur.fetchall()
    changed = 0

    for row in rows:
        row_id = row[0]
        old_strategy = row[1]
        old_timeframe = row[2] if "timeframe" in cols else ""

        new_strategy = canonicalize_strategy_name(old_strategy)
        new_timeframe = canonicalize_timeframe(old_timeframe)

        if old_strategy == new_strategy and old_timeframe == new_timeframe:
            continue

        if "timeframe" in cols:
            cur.execute(
                f"""
                UPDATE {table}
                SET strategy=%s,
                    timeframe=%s
                WHERE id=%s
                """,
                (new_strategy, new_timeframe, row_id),
            )
        else:
            cur.execute(
                f"""
                UPDATE {table}
                SET strategy=%s
                WHERE id=%s
                """,
                (new_strategy, row_id),
            )

        changed += 1

    return changed


def normalize_payload(cur, *, symbols: list[str]) -> int:
    cols = columns_for(cur, "trades")

    if "payload" not in cols:
        return 0

    where = ""
    params: list[object] = []

    if "symbol" in cols and symbols:
        where = "WHERE symbol = ANY(%s)"
        params.append(symbols)

    cur.execute(
        f"""
        SELECT id,
               payload->>'strategy',
               COALESCE(payload->>'timeframe', payload->>'tf', '')
        FROM trades
        {where}
        """,
        params,
    )

    changed = 0

    for row_id, strategy, timeframe in cur.fetchall():
        canonical_strategy = canonicalize_strategy_name(strategy)
        canonical_tf = canonicalize_timeframe(timeframe)

        if not canonical_strategy and not canonical_tf:
            continue

        cur.execute(
            """
            UPDATE trades
            SET payload =
                jsonb_set(
                    jsonb_set(
                        COALESCE(payload, '{}'::jsonb),
                        '{strategy}',
                        to_jsonb(%s::text),
                        true
                    ),
                    '{timeframe}',
                    to_jsonb(%s::text),
                    true
                )
            WHERE id=%s
            """,
            (canonical_strategy, canonical_tf, row_id),
        )

        changed += 1

    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    total = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for table in TABLES:
                changed = normalize_table(cur, table=table, symbols=symbols)
                total += changed
                print(
                    "STRATEGY_CANONICALIZER_TABLE "
                    f"table={table} changed={changed}",
                    flush=True,
                )

            payload_changed = normalize_payload(cur, symbols=symbols)
            total += payload_changed

            print(
                "STRATEGY_CANONICALIZER_PAYLOAD "
                f"table=trades changed={payload_changed}",
                flush=True,
            )

        if args.apply:
            conn.commit()
        else:
            conn.rollback()

    print(
        "STRATEGY_CANONICALIZER_SUMMARY "
        f"symbols={len(symbols)} changed={total} applied={args.apply}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
