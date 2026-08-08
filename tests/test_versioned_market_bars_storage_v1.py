from pathlib import Path

from finam_core.research.versioned_market_bars_v1 import (
    DDL,
)


SCRIPT = Path(
    "scripts/research/"
    "build_versioned_market_bars_storage_v1.py"
)


def test_storage_script_exists():
    assert SCRIPT.is_file()


def test_ddl_has_versioned_unique_identity():
    normalized = " ".join(
        DDL.lower().split()
    )

    assert (
        "unique ( dataset_version, symbol, timeframe, ts )"
        in normalized
    )


def test_ddl_prohibits_default_dataset():
    normalized = " ".join(
        DDL.lower().split()
    )

    assert (
        "check (dataset_version <> 'default')"
        in normalized
    )


def test_ddl_contains_no_update_or_delete():
    normalized = DDL.lower()

    assert "do update" not in normalized
    assert "update analytics.research_market_bars" not in normalized
    assert "delete from analytics.research_market_bars" not in normalized


def test_storage_builder_only_executes_ddl():
    source = SCRIPT.read_text().lower()

    forbidden = (
        "insert into analytics.research_market_bars",
        "update analytics.research_market_bars",
        "delete from analytics.research_market_bars",
        "truncate analytics.research_market_bars",
    )

    for token in forbidden:
        assert token not in source
