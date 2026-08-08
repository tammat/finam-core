from datetime import datetime, timezone
from decimal import Decimal

import pytest

from finam_core.research.versioned_market_bars_v1 import (
    DDL,
    NATIVE_FINAM_M5_V1,
    VersionedMarketBarsContractError,
    build_bar,
    insert_sql,
    payload_hash,
    verify_existing_row,
)


TS = datetime(
    2026, 8, 8, 10, 25,
    tzinfo=timezone.utc,
)


def make_bar(**overrides):
    values = {
        "dataset_version": NATIVE_FINAM_M5_V1,
        "symbol": "NGU6@RTSX",
        "timeframe": "M5",
        "ts": TS,
        "open": Decimal("2.746"),
        "high": Decimal("2.747"),
        "low": Decimal("2.745"),
        "close": Decimal("2.746"),
        "volume": Decimal("10"),
        "provider": "FINAM_GRPC",
        "provider_data_version": "FINAM_NATIVE_M5_V1",
    }

    values.update(overrides)
    return build_bar(**values)


def existing_from_bar(bar):
    return {
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "provider": bar.provider,
        "provider_data_version": bar.provider_data_version,
        "source_payload_hash": bar.source_payload_hash,
    }


def test_payload_hash_is_deterministic():
    first = payload_hash({
        "b": "2",
        "a": "1",
    })

    second = payload_hash({
        "a": "1",
        "b": "2",
    })

    assert first == second
    assert len(first) == 64


def test_build_bar_hash_is_deterministic():
    first = make_bar()
    second = make_bar()

    assert first == second
    assert first.source_payload_hash == second.source_payload_hash
    assert len(first.source_payload_hash) == 64


def test_default_dataset_is_reserved_for_legacy():
    with pytest.raises(
        VersionedMarketBarsContractError,
        match="default_dataset_version_reserved_for_legacy",
    ):
        make_bar(dataset_version="default")


def test_timezone_naive_timestamp_is_rejected():
    with pytest.raises(
        VersionedMarketBarsContractError,
        match="bar_timestamp_must_be_timezone_aware",
    ):
        make_bar(
            ts=datetime(2026, 8, 8, 10, 25)
        )


@pytest.mark.parametrize(
    "field,value,error",
    [
        (
            "open",
            Decimal("0"),
            "ohlc_must_be_positive",
        ),
        (
            "close",
            Decimal("-1"),
            "ohlc_must_be_positive",
        ),
        (
            "volume",
            Decimal("-1"),
            "volume_must_be_non_negative",
        ),
        (
            "high",
            Decimal("2.744"),
            "high_below_ohlc",
        ),
        (
            "low",
            Decimal("2.748"),
            "low_above_ohlc",
        ),
    ],
)
def test_invalid_bar_contract_fails_closed(
    field,
    value,
    error,
):
    with pytest.raises(
        VersionedMarketBarsContractError,
        match=error,
    ):
        make_bar(**{field: value})


def test_identical_existing_row_is_idempotent():
    bar = make_bar()

    verify_existing_row(
        existing_from_bar(bar),
        bar,
    )


def test_numeric_scale_difference_is_not_a_conflict():
    bar = make_bar(
        close=Decimal("2.900"),
        high=Decimal("2.900"),
    )

    existing = existing_from_bar(bar)
    existing["close"] = Decimal("2.9")
    existing["high"] = Decimal("2.9000")

    verify_existing_row(
        existing,
        bar,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("open", Decimal("2.700")),
        ("provider", "OTHER_PROVIDER"),
        (
            "provider_data_version",
            "OTHER_VERSION",
        ),
        (
            "source_payload_hash",
            "0" * 64,
        ),
    ],
)
def test_changed_existing_row_fails_closed(
    field,
    value,
):
    bar = make_bar()
    existing = existing_from_bar(bar)
    existing[field] = value

    with pytest.raises(
        VersionedMarketBarsContractError,
        match="immutable_dataset_conflict",
    ):
        verify_existing_row(
            existing,
            bar,
        )


def test_insert_sql_never_updates_existing_bar():
    normalized = " ".join(
        insert_sql().lower().split()
    )

    assert "on conflict" in normalized
    assert "do nothing" in normalized
    assert "do update" not in normalized
    assert "update analytics.research_market_bars" not in normalized


def test_ddl_identity_includes_dataset_version():
    normalized = " ".join(
        DDL.lower().split()
    )

    assert (
        "unique ( dataset_version, symbol, timeframe, ts )"
        in normalized
    )

    assert "dataset_version <> 'default'" in normalized
