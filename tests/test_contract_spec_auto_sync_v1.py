from decimal import Decimal
from pathlib import Path

import scripts.sync_market_contract_specs_v1 as sync


ROOT = Path(__file__).resolve().parents[1]


def test_futures_multiplier_comes_from_moex_step_value(monkeypatch) -> None:
    monkeypatch.setattr(sync, "_get", lambda _url: {"securities": {
        "columns": ["SECID","SECNAME","LOTVOLUME","MINSTEP","STEPPRICE","DECIMALS",
                    "INITIALMARGIN","BUYSELLFEE","SCALPERFEE"],
        "data": [["BRQ6","Brent",1,0.01,7.95,2,10000,3.5,1.75]],
    }})
    spec = sync.fetch_spec("BRQ6@RTSX")
    assert spec.lot_size == Decimal("1")
    assert spec.quantity_step == Decimal("1")
    assert spec.underlying_units == Decimal("1")
    assert spec.tick_size == Decimal("0.01")
    assert spec.tick_value == Decimal("7.95")
    assert spec.contract_multiplier == Decimal("795")


def test_equity_requires_execution_board_and_positive_fields(monkeypatch) -> None:
    monkeypatch.setattr(sync, "_get", lambda _url: {"securities": {
        "columns": ["SECID","BOARDID","SECNAME","LOTSIZE","MINSTEP","DECIMALS"],
        "data": [["SBER","TQBR","Сбербанк",10,0.01,2]],
    }})
    spec = sync.fetch_spec("SBER@MISX")
    assert spec.asset_class == "EQUITY"
    assert spec.lot_size == Decimal("10")
    assert spec.quantity_step == Decimal("10")
    assert spec.contract_multiplier == Decimal("1")


def test_invalid_reference_is_never_replaced_with_one(monkeypatch) -> None:
    monkeypatch.setattr(sync, "_get", lambda _url: {"securities": {
        "columns": ["SECID","BOARDID","LOTSIZE","MINSTEP","DECIMALS"],
        "data": [["SBER","TQBR",None,0.01,2]],
    }})
    try:
        sync.fetch_spec("SBER@MISX")
    except ValueError as exc:
        assert str(exc) == "INVALID_LOTSIZE"
    else:
        raise AssertionError("invalid source must fail closed")


def test_unavailable_foreign_share_reference_is_not_an_edge_cycle_failure(monkeypatch) -> None:
    monkeypatch.setattr(sync, "_get", lambda _url: {"securities": {
        "columns": ["SECID", "BOARDID"], "data": [],
    }})
    try:
        sync.fetch_spec("AAPL-RM@MISX")
    except sync.SpecNotApplicable as exc:
        assert str(exc) == "MOEX_FOREIGN_SHARE_REFERENCE_UNAVAILABLE"
    else:
        raise AssertionError("unavailable foreign reference must be explicitly skipped")


def test_active_equity_missing_execution_board_still_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(sync, "_get", lambda _url: {"securities": {
        "columns": ["SECID", "BOARDID"], "data": [],
    }})
    try:
        sync.fetch_spec("SBER@MISX")
    except ValueError as exc:
        assert not isinstance(exc, sync.SpecNotApplicable)
        assert str(exc) == "MOEX_EXECUTION_BOARD_NOT_FOUND"
    else:
        raise AssertionError("active equity without TQBR reference must fail closed")


def test_sync_is_db_audited_and_first_autonomous_step() -> None:
    migration = (ROOT / "sql/analytics/093_contract_spec_auto_sync_v1.sql").read_text()
    runner = (ROOT / "src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    script = (ROOT / "src/scripts/sync_market_contract_specs_v1.py").read_text()
    assert "contract_spec_sync_run_v1" in migration
    assert "contract_spec_sync_item_v1" in migration
    assert "SYNC_CONTRACT_SPECS" in migration and "SYNC_CONTRACT_SPECS" in runner
    assert "step_order=step_order+100" in migration
    assert "source_payload" in script
    assert "MISSING_SPEC_FALLBACK" not in script
