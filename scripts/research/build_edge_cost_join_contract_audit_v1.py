#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUT = pathlib.Path("/tmp/edge_cost_join_contract_audit_v1")

OBSERVATION_FILE = OUT / "observation_keys.tsv"
TRADE_FILE = OUT / "trade_keys.tsv"
JOIN_FILE = OUT / "join_cardinality.tsv"
OOS_FILE = OUT / "oos_cardinality.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []

    with psycopg2.connect(build_psycopg_url()) as connection:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe,
                    count(*)::bigint AS observation_count,
                    count(DISTINCT parameter_hash)::bigint
                        AS parameter_hash_count,
                    count(DISTINCT market_regime)::bigint
                        AS market_regime_count,
                    count(DISTINCT strategy_version)::bigint
                        AS strategy_version_count,
                    sum(trades)::bigint AS declared_trade_count
                FROM analytics.edge_observation_v1
                GROUP BY
                    run_uuid,
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe
                ORDER BY observation_count DESC
                """
            )
            observation_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe,
                    count(*)::bigint AS actual_trade_count,
                    count(DISTINCT trade_no)::bigint
                        AS distinct_trade_no_count,
                    sum(gross_pnl)::numeric AS gross_pnl,
                    sum(commission)::numeric AS commission,
                    sum(slippage)::numeric AS slippage,
                    sum(net_pnl)::numeric AS net_pnl
                FROM analytics.research_trade_v1
                GROUP BY
                    run_uuid,
                    research_code,
                    strategy_code,
                    symbol,
                    timeframe
                ORDER BY actual_trade_count DESC
                """
            )
            trade_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                WITH observations AS (
                    SELECT
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe,
                        count(*)::bigint AS observation_count,
                        count(DISTINCT parameter_hash)::bigint
                            AS parameter_hash_count,
                        count(DISTINCT market_regime)::bigint
                            AS market_regime_count,
                        sum(trades)::bigint AS declared_trade_count
                    FROM analytics.edge_observation_v1
                    GROUP BY
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe
                ),
                trades AS (
                    SELECT
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe,
                        count(*)::bigint AS actual_trade_count,
                        count(DISTINCT trade_no)::bigint
                            AS distinct_trade_no_count,
                        sum(gross_pnl)::numeric AS gross_pnl,
                        sum(commission)::numeric AS commission,
                        sum(slippage)::numeric AS slippage,
                        sum(net_pnl)::numeric AS net_pnl
                    FROM analytics.research_trade_v1
                    GROUP BY
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe
                )
                SELECT
                    o.run_uuid::text,
                    o.research_code,
                    o.strategy_code,
                    o.symbol,
                    o.timeframe,
                    o.observation_count,
                    o.parameter_hash_count,
                    o.market_regime_count,
                    o.declared_trade_count,
                    COALESCE(t.actual_trade_count, 0)::bigint
                        AS actual_trade_count,
                    COALESCE(t.distinct_trade_no_count, 0)::bigint
                        AS distinct_trade_no_count,
                    COALESCE(t.gross_pnl, 0)::numeric AS gross_pnl,
                    COALESCE(t.commission, 0)::numeric AS commission,
                    COALESCE(t.slippage, 0)::numeric AS slippage,
                    COALESCE(t.net_pnl, 0)::numeric AS net_pnl,
                    CASE
                        WHEN o.observation_count <> 1
                            THEN 'AMBIGUOUS_OBSERVATION_KEY'
                        WHEN o.parameter_hash_count <> 1
                            THEN 'AMBIGUOUS_PARAMETER_SET'
                        WHEN o.market_regime_count <> 1
                            THEN 'AMBIGUOUS_MARKET_REGIME'
                        WHEN t.run_uuid IS NULL
                            THEN 'TRADES_MISSING'
                        WHEN t.actual_trade_count
                             <> t.distinct_trade_no_count
                            THEN 'DUPLICATE_TRADE_NO'
                        WHEN o.declared_trade_count
                             <> t.actual_trade_count
                            THEN 'TRADE_COUNT_MISMATCH'
                        ELSE 'JOIN_SAFE'
                    END AS join_status
                FROM observations o
                LEFT JOIN trades t
                  ON t.run_uuid = o.run_uuid
                 AND t.research_code = o.research_code
                 AND t.strategy_code = o.strategy_code
                 AND t.symbol = o.symbol
                 AND t.timeframe = o.timeframe
                ORDER BY
                    CASE
                        WHEN o.observation_count = 1
                         AND o.parameter_hash_count = 1
                         AND o.market_regime_count = 1
                         AND t.run_uuid IS NOT NULL
                         AND t.actual_trade_count
                             = t.distinct_trade_no_count
                         AND o.declared_trade_count
                             = t.actual_trade_count
                            THEN 1
                        ELSE 0
                    END,
                    o.symbol,
                    o.strategy_code,
                    o.timeframe
                """
            )
            join_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    count(*)::bigint AS row_count,
                    count(DISTINCT build_id)::bigint AS build_count,
                    count(DISTINCT source_version)::bigint
                        AS source_version_count,
                    max(refreshed_at) AS latest_refreshed_at,
                    CASE
                        WHEN count(*) = 1
                            THEN 'UNIQUE_CURRENT_ROW'
                        ELSE 'MULTIPLE_OOS_ROWS'
                    END AS cardinality_status
                FROM marketcore_ui.edge_oos_validation_v1
                GROUP BY
                    symbol,
                    strategy,
                    timeframe,
                    side
                ORDER BY row_count DESC
                """
            )
            oos_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

    unsafe_join_rows = [
        row
        for row in join_rows
        if row["join_status"] != "JOIN_SAFE"
    ]

    safe_join_count = len(join_rows) - len(unsafe_join_rows)
    ambiguous_observation_count = sum(
        row["join_status"] in {
            "AMBIGUOUS_OBSERVATION_KEY",
            "AMBIGUOUS_PARAMETER_SET",
            "AMBIGUOUS_MARKET_REGIME",
        }
        for row in join_rows
    )
    missing_trade_count = sum(
        row["join_status"] == "TRADES_MISSING"
        for row in join_rows
    )
    trade_count_mismatch_count = sum(
        row["join_status"] == "TRADE_COUNT_MISMATCH"
        for row in join_rows
    )
    duplicate_trade_no_count = sum(
        row["join_status"] == "DUPLICATE_TRADE_NO"
        for row in join_rows
    )
    ambiguous_oos_count = sum(
        row["cardinality_status"] != "UNIQUE_CURRENT_ROW"
        for row in oos_rows
    )

    for row in unsafe_join_rows:
        unresolved.append(
            {
                "scope": "EDGE_TRADE_JOIN",
                "identity": (
                    f"{row['run_uuid']}:"
                    f"{row['strategy_code']}:"
                    f"{row['symbol']}:"
                    f"{row['timeframe']}"
                ),
                "reason": str(row["join_status"]),
            }
        )

    for row in oos_rows:
        if row["cardinality_status"] == "UNIQUE_CURRENT_ROW":
            continue

        unresolved.append(
            {
                "scope": "OOS_JOIN",
                "identity": (
                    f"{row['symbol']}:"
                    f"{row['strategy']}:"
                    f"{row['timeframe']}:"
                    f"{row['side']}"
                ),
                "reason": "MULTIPLE_OOS_ROWS",
            }
        )

    write_tsv(
        OBSERVATION_FILE,
        (
            "run_uuid",
            "research_code",
            "strategy_code",
            "symbol",
            "timeframe",
            "observation_count",
            "parameter_hash_count",
            "market_regime_count",
            "strategy_version_count",
            "declared_trade_count",
        ),
        observation_rows,
    )

    write_tsv(
        TRADE_FILE,
        (
            "run_uuid",
            "research_code",
            "strategy_code",
            "symbol",
            "timeframe",
            "actual_trade_count",
            "distinct_trade_no_count",
            "gross_pnl",
            "commission",
            "slippage",
            "net_pnl",
        ),
        trade_rows,
    )

    write_tsv(
        JOIN_FILE,
        (
            "run_uuid",
            "research_code",
            "strategy_code",
            "symbol",
            "timeframe",
            "observation_count",
            "parameter_hash_count",
            "market_regime_count",
            "declared_trade_count",
            "actual_trade_count",
            "distinct_trade_no_count",
            "gross_pnl",
            "commission",
            "slippage",
            "net_pnl",
            "join_status",
        ),
        join_rows,
    )

    write_tsv(
        OOS_FILE,
        (
            "symbol",
            "strategy",
            "timeframe",
            "side",
            "row_count",
            "build_count",
            "source_version_count",
            "latest_refreshed_at",
            "cardinality_status",
        ),
        oos_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE COST JOIN CONTRACT AUDIT V1\n")
        stream.write("===============================\n\n")
        stream.write("MODE=READ_ONLY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write(
            "JOIN_KEY="
            "run_uuid,research_code,strategy_code,symbol,timeframe\n"
        )
        stream.write(
            "PARAMETER_HASH_PRESENT_IN_TRADES=0\n"
        )
        stream.write(
            "MARKET_REGIME_PRESENT_IN_TRADES=0\n"
        )
        stream.write(
            f"JOIN_GROUP_COUNT={len(join_rows)}\n"
        )
        stream.write(
            f"SAFE_JOIN_COUNT={safe_join_count}\n"
        )
        stream.write(
            "AMBIGUOUS_OBSERVATION_COUNT="
            f"{ambiguous_observation_count}\n"
        )
        stream.write(
            f"MISSING_TRADE_COUNT={missing_trade_count}\n"
        )
        stream.write(
            "TRADE_COUNT_MISMATCH_COUNT="
            f"{trade_count_mismatch_count}\n"
        )
        stream.write(
            "DUPLICATE_TRADE_NO_COUNT="
            f"{duplicate_trade_no_count}\n"
        )
        stream.write(
            f"AMBIGUOUS_OOS_COUNT={ambiguous_oos_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== EDGE COST JOIN CONTRACT AUDIT V1 ===")
    print(f"join_group_count={len(join_rows)}")
    print(f"safe_join_count={safe_join_count}")
    print(
        "ambiguous_observation_count="
        f"{ambiguous_observation_count}"
    )
    print(f"missing_trade_count={missing_trade_count}")
    print(
        "trade_count_mismatch_count="
        f"{trade_count_mismatch_count}"
    )
    print(
        "duplicate_trade_no_count="
        f"{duplicate_trade_no_count}"
    )
    print(f"ambiguous_oos_count={ambiguous_oos_count}")
    print(f"unresolved_count={len(unresolved)}")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_COST_JOIN_CONTRACT_AUDIT_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
