from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, Sequence


TABLE_SCHEMA = "analytics"
TABLE_NAME = "research_market_bars_v1"

DEFAULT_DATASET_VERSION = "default"
NATIVE_FINAM_M5_V1 = "NATIVE_FINAM_M5_V1"


class VersionedMarketBarsContractError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VersionedResearchBar:
    dataset_version: str
    symbol: str
    timeframe: str
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    provider: str
    provider_data_version: str
    source_payload_hash: str


def canonical_payload(
    *,
    symbol: str,
    timeframe: str,
    ts: datetime,
    open: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    provider: str,
    provider_data_version: str,
) -> dict[str, str]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "ts": ts.isoformat(),
        "open": str(open),
        "high": str(high),
        "low": str(low),
        "close": str(close),
        "volume": str(volume),
        "provider": provider,
        "provider_data_version": provider_data_version,
    }


def payload_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def build_bar(
    *,
    dataset_version: str,
    symbol: str,
    timeframe: str,
    ts: datetime,
    open: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    provider: str,
    provider_data_version: str,
) -> VersionedResearchBar:
    if not dataset_version.strip():
        raise VersionedMarketBarsContractError(
            "dataset_version_empty"
        )

    if dataset_version == DEFAULT_DATASET_VERSION:
        raise VersionedMarketBarsContractError(
            "default_dataset_version_reserved_for_legacy"
        )

    if ts.tzinfo is None:
        raise VersionedMarketBarsContractError(
            "bar_timestamp_must_be_timezone_aware"
        )

    if any(
        value <= 0
        for value in (open, high, low, close)
    ):
        raise VersionedMarketBarsContractError(
            "ohlc_must_be_positive"
        )

    if volume < 0:
        raise VersionedMarketBarsContractError(
            "volume_must_be_non_negative"
        )

    if high < max(open, close):
        raise VersionedMarketBarsContractError(
            "high_below_ohlc"
        )

    if low > min(open, close):
        raise VersionedMarketBarsContractError(
            "low_above_ohlc"
        )

    payload = canonical_payload(
        symbol=symbol,
        timeframe=timeframe,
        ts=ts,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        provider=provider,
        provider_data_version=provider_data_version,
    )

    return VersionedResearchBar(
        dataset_version=dataset_version,
        symbol=symbol,
        timeframe=timeframe,
        ts=ts,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        provider=provider,
        provider_data_version=provider_data_version,
        source_payload_hash=payload_hash(payload),
    )


DDL = """
CREATE TABLE IF NOT EXISTS analytics.research_market_bars_v1 (
    id bigserial PRIMARY KEY,

    dataset_version text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    ts timestamptz NOT NULL,

    open numeric NOT NULL,
    high numeric NOT NULL,
    low numeric NOT NULL,
    close numeric NOT NULL,
    volume numeric NOT NULL,

    provider text NOT NULL,
    provider_data_version text NOT NULL,
    source_payload_hash text NOT NULL,

    ingested_at timestamptz NOT NULL DEFAULT now(),

    UNIQUE (
        dataset_version,
        symbol,
        timeframe,
        ts
    ),

    CHECK (dataset_version <> ''),
    CHECK (dataset_version <> 'default'),
    CHECK (open > 0),
    CHECK (high > 0),
    CHECK (low > 0),
    CHECK (close > 0),
    CHECK (volume >= 0),
    CHECK (high >= open),
    CHECK (high >= close),
    CHECK (high >= low),
    CHECK (low <= open),
    CHECK (low <= close),
    CHECK (low <= high)
);

CREATE INDEX IF NOT EXISTS
    ix_research_market_bars_v1_lookup
ON analytics.research_market_bars_v1 (
    dataset_version,
    symbol,
    timeframe,
    ts DESC
);
"""


def insert_sql() -> str:
    # Намеренно нет ON CONFLICT DO UPDATE.
    return """
        INSERT INTO analytics.research_market_bars_v1 (
            dataset_version,
            symbol,
            timeframe,
            ts,
            open,
            high,
            low,
            close,
            volume,
            provider,
            provider_data_version,
            source_payload_hash
        )
        VALUES (
            %s,%s,%s,%s,
            %s,%s,%s,%s,
            %s,%s,%s,%s
        )
        ON CONFLICT (
            dataset_version,
            symbol,
            timeframe,
            ts
        )
        DO NOTHING
    """


def bar_values(
    bar: VersionedResearchBar,
) -> tuple[Any, ...]:
    return (
        bar.dataset_version,
        bar.symbol,
        bar.timeframe,
        bar.ts,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.provider,
        bar.provider_data_version,
        bar.source_payload_hash,
    )


def verify_existing_row(
    existing: Mapping[str, Any],
    incoming: VersionedResearchBar,
) -> None:
    fields: Sequence[str] = (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "provider",
        "provider_data_version",
        "source_payload_hash",
    )

    expected = {
        "open": incoming.open,
        "high": incoming.high,
        "low": incoming.low,
        "close": incoming.close,
        "volume": incoming.volume,
        "provider": incoming.provider,
        "provider_data_version": incoming.provider_data_version,
        "source_payload_hash": incoming.source_payload_hash,
    }

    numeric_fields = {
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    mismatches = []

    for field in fields:
        actual_value = existing[field]
        expected_value = expected[field]

        if field in numeric_fields:
            equal = (
                Decimal(str(actual_value))
                == Decimal(str(expected_value))
            )
        else:
            equal = (
                str(actual_value)
                == str(expected_value)
            )

        if not equal:
            mismatches.append(field)

    if mismatches:
        raise VersionedMarketBarsContractError(
            "immutable_dataset_conflict:"
            + ",".join(mismatches)
        )
