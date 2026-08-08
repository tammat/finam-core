from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from psycopg2.extras import RealDictCursor

from finam_core.research.versioned_market_bars_v1 import (
    VersionedResearchBar,
    bar_values,
    insert_sql,
    verify_existing_row,
)


SOURCE_VERSION = "VERSIONED_MARKET_BARS_INGESTION_V1"


@dataclass(frozen=True, slots=True)
class VersionedMarketBarsIngestionResult:
    rows_seen: int
    rows_inserted: int
    rows_identical: int


SELECT_EXISTING_SQL = """
    SELECT
        open,
        high,
        low,
        close,
        volume,
        provider,
        provider_data_version,
        source_payload_hash
    FROM analytics.research_market_bars_v1
    WHERE dataset_version = %s
      AND symbol = %s
      AND timeframe = %s
      AND ts = %s
"""


def identity_values(
    bar: VersionedResearchBar,
) -> tuple[object, ...]:
    return (
        bar.dataset_version,
        bar.symbol,
        bar.timeframe,
        bar.ts,
    )


def ingest_one(
    cursor: RealDictCursor,
    bar: VersionedResearchBar,
) -> str:
    cursor.execute(
        SELECT_EXISTING_SQL,
        identity_values(bar),
    )

    existing = cursor.fetchone()

    if existing is not None:
        verify_existing_row(
            existing,
            bar,
        )
        return "IDENTICAL"

    cursor.execute(
        insert_sql(),
        bar_values(bar),
    )

    # rowcount=1: наша транзакция вставила строку.
    if cursor.rowcount == 1:
        return "INSERTED"

    # Возможен concurrent insert между SELECT и INSERT.
    # DO NOTHING не должен скрывать payload conflict.
    cursor.execute(
        SELECT_EXISTING_SQL,
        identity_values(bar),
    )

    existing = cursor.fetchone()

    if existing is None:
        raise RuntimeError(
            "versioned_market_bar_conflict_without_existing_row"
        )

    verify_existing_row(
        existing,
        bar,
    )

    return "IDENTICAL"


def ingest_many(
    cursor: RealDictCursor,
    bars: Iterable[VersionedResearchBar],
) -> VersionedMarketBarsIngestionResult:
    rows = list(bars)

    inserted = 0
    identical = 0

    # Один dataset identity не должен содержать дублей
    # внутри одного ingestion payload.
    seen = set()

    for bar in rows:
        identity = identity_values(bar)

        if identity in seen:
            raise RuntimeError(
                "duplicate_bar_identity_in_ingestion_payload:"
                f"{identity}"
            )

        seen.add(identity)

        outcome = ingest_one(
            cursor,
            bar,
        )

        if outcome == "INSERTED":
            inserted += 1
        elif outcome == "IDENTICAL":
            identical += 1
        else:
            raise RuntimeError(
                f"unexpected_ingestion_outcome:{outcome}"
            )

    return VersionedMarketBarsIngestionResult(
        rows_seen=len(rows),
        rows_inserted=inserted,
        rows_identical=identical,
    )
