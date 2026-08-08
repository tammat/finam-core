from __future__ import annotations

from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


RUNNER_VERSION = "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
TOLERANCE = Decimal("0.0001")


def classify_monetary_validity(row: dict) -> str:
    trades = int(row["trades"] or 0)
    observed = row["observed_multiplier"]
    exact = row["exact_spec_multiplier"]

    if trades == 0 or observed is None:
        return "NO_TRADES"

    # Исторический BRZ6 ATR использовал отдельную динамическую
    # CBR-модель. До trade-level CBR audit ranking запрещён.
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


def load_monetary_rows(
    cursor: RealDictCursor,
) -> list[dict]:
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


def load_monetary_validity_by_run() -> dict[str, dict]:
    connection = psycopg2.connect(build_psycopg_url())

    try:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            rows = load_monetary_rows(cursor)

        result: dict[str, dict] = {}

        for row in rows:
            status = classify_monetary_validity(row)

            result[str(row["run_uuid"])] = {
                "monetary_status": status,
                "ranking_allowed": (
                    status == "VALID_MONETARY"
                ),
                "observed_multiplier": (
                    row["observed_multiplier"]
                ),
                "exact_spec_multiplier": (
                    row["exact_spec_multiplier"]
                ),
            }

        return result

    finally:
        connection.close()
