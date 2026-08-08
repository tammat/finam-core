#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


RUNNER_VERSION = "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
TOLERANCE = Decimal("0.0001")


def classify(row: dict) -> str:
    trades = int(row["trades"] or 0)
    observed = row["observed_multiplier"]
    exact = row["exact_spec_multiplier"]

    if trades == 0 or observed is None:
        return "NO_TRADES"

    # Исторический BRZ6 ATR использовал отдельную динамическую
    # CBR-модель. До trade-level CBR audit не разрешаем ranking.
    if (
        row["symbol"] == "BRZ6@RTSX"
        and row["strategy_code"] == "ATR_IMPULSE_V1"
    ):
        return "UNRESOLVED_CBR_MONETARY"

    if exact is None:
        return "UNRESOLVED_NO_SPEC"

    observed_d = Decimal(str(observed))
    exact_d = Decimal(str(exact))

    if abs(observed_d - exact_d) <= TOLERANCE:
        return "VALID_MONETARY"

    return "LEGACY_INVALID_MONETARY"


def load_rows(cursor: RealDictCursor) -> list[dict]:
    cursor.execute(
        """
        WITH run_signature AS (
            SELECT
                r.run_uuid::text AS run_uuid,
                r.symbol,
                r.strategy_code,
                count(t.*)::bigint AS trades,
                avg(
                    abs(t.exit_price - t.entry_price)
                ) AS avg_delta,
                avg(
                    abs(t.gross_pnl)
                ) AS avg_gross
            FROM analytics.edge_lab_run_v1 r
            LEFT JOIN analytics.research_trade_v1 t
              ON t.run_uuid = r.run_uuid
            WHERE r.runner_version = %s
              AND r.status_code = 'DONE'
              AND r.symbol LIKE '%%@RTSX'
            GROUP BY
                r.run_uuid,
                r.symbol,
                r.strategy_code
        ),
        signature AS (
            SELECT
                *,
                avg_gross / NULLIF(avg_delta, 0)
                    AS observed_multiplier
            FROM run_signature
        ),
        spec AS (
            SELECT DISTINCT ON (symbol)
                symbol,
                contract_multiplier,
                source_version
            FROM analytics.market_contract_spec_v1
            WHERE source_version =
                  'MOEX_ISS_CONTRACT_SPEC_V1'
            ORDER BY symbol, valid_from DESC
        )
        SELECT
            s.run_uuid,
            s.symbol,
            s.strategy_code,
            s.trades,
            s.observed_multiplier,
            spec.contract_multiplier
                AS exact_spec_multiplier,
            spec.source_version
                AS contract_spec_source
        FROM signature s
        LEFT JOIN spec
          ON spec.symbol = s.symbol
        ORDER BY
            s.symbol,
            s.strategy_code,
            s.run_uuid
        """,
        (RUNNER_VERSION,),
    )

    return list(cursor.fetchall())


def main() -> int:
    connection = psycopg2.connect(build_psycopg_url())

    try:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            rows = load_rows(cursor)

        counts: Counter[str] = Counter()
        trade_counts: Counter[str] = Counter()
        ranking_allowed = 0

        for row in rows:
            status = classify(row)
            counts[status] += 1
            trade_counts[status] += int(row["trades"] or 0)

            allowed = int(status == "VALID_MONETARY")
            ranking_allowed += allowed

            print(
                "LINEAGE_ROW "
                f"run_uuid={row['run_uuid']} "
                f"symbol={row['symbol']} "
                f"strategy={row['strategy_code']} "
                f"trades={row['trades']} "
                f"observed_multiplier="
                f"{row['observed_multiplier']} "
                f"exact_spec_multiplier="
                f"{row['exact_spec_multiplier']} "
                f"monetary_status={status} "
                f"ranking_allowed={allowed}"
            )

        print(
            "=== POSTGRESQL FUTURES "
            "MONETARY VALIDITY LINEAGE V1 ==="
        )
        print(f"total_runs={len(rows)}")

        for status in (
            "VALID_MONETARY",
            "LEGACY_INVALID_MONETARY",
            "UNRESOLVED_NO_SPEC",
            "UNRESOLVED_CBR_MONETARY",
            "NO_TRADES",
        ):
            print(
                f"{status.lower()}_runs="
                f"{counts[status]}"
            )
            print(
                f"{status.lower()}_trades="
                f"{trade_counts[status]}"
            )

        print(f"ranking_allowed_runs={ranking_allowed}")
        print("fail_closed=1")
        print("db_writes_performed=0")
        print("strategy_changed=0")
        print("risk_engine_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_MONETARY_VALIDITY_LINEAGE_V1_READY"
        )

        return 0

    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
