from __future__ import annotations

from finam_core.storage.instrument_spec_repository import InstrumentSpecRepository


class _Cursor:
    def __init__(self, canonical_row):
        self.canonical_row = canonical_row
        self.executed = []
        self._row = None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "market_contract_spec_v1" in sql:
            self._row = self.canonical_row
        elif "to_regclass" in sql:
            self._row = {"relation": None}
        else:
            raise AssertionError("legacy table must not be queried without to_regclass")

    def fetchone(self):
        return self._row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, **_kwargs):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


def test_canonical_moex_spec_and_db_fee_profile_are_preferred(monkeypatch) -> None:
    row = {
        "symbol": "BRQ6@RTSX",
        "base_symbol": "BRQ6",
        "asset_class": "FUTURES",
        "min_price_step": 0.01,
        "step_value": 7.84049,
        "lot_size": 10,
        "currency": "RUB",
        "broker_fee": 1,
        "exchange_fee": 0.5,
        "clearing_fee": 0.25,
        "tax_rate": 0.13,
    }
    cursor = _Cursor(row)
    repository = InstrumentSpecRepository("unused")
    monkeypatch.setattr(repository, "_connect", lambda: _Connection(cursor))

    assert repository.get_by_symbol("brq6@rtsx") == row
    sql, params = cursor.executed[0]
    assert "analytics.market_contract_spec_v1" in sql
    assert "public.fee_profiles" in sql
    assert params == ("BRQ6@RTSX", "BRQ6@RTSX")


def test_missing_canonical_and_legacy_tables_returns_none(monkeypatch) -> None:
    cursor = _Cursor(None)
    repository = InstrumentSpecRepository("unused")
    monkeypatch.setattr(repository, "_connect", lambda: _Connection(cursor))

    assert repository.get_by_symbol("UNKNOWN@RTSX") is None
    assert any("to_regclass" in sql for sql, _params in cursor.executed)
