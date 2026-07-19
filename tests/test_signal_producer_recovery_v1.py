from datetime import datetime, timezone
from pathlib import Path

from finam_core.adapters.grpc.market_data import FinamMarketDataClient
from finam_core.analytics.signal_repository import SignalRepository
from finam_core.data.runtime_symbol_reload_service import RuntimeSymbolReloadService


ROOT = Path(__file__).resolve().parents[1]


class _Timestamp:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def ToDatetime(self, tzinfo=None):
        return self.value.astimezone(tzinfo)


class _Quote:
    def __init__(self, value: datetime) -> None:
        self.timestamp = _Timestamp(value)


def test_market_data_keeps_exchange_timestamp() -> None:
    expected = datetime(2026, 7, 19, 7, 30, tzinfo=timezone.utc)
    assert FinamMarketDataClient._quote_timestamp(_Quote(expected)) == expected


def test_pipeline_blocks_stale_quote_before_bar_storage() -> None:
    source = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert 'event.get("ts") is None and event.get("timestamp") is None' in source
    gate = source.index("if market_data_live:")
    storage = source.index("self._record_live_quote_to_storage(", gate)
    stale_block = source.index("PIPE_STALE_QUOTE_STORAGE_BLOCK", storage)
    assert gate < storage < stale_block


class _Cursor:
    def __init__(self) -> None:
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, params):
        self.executions.append((query, params))


class _Connection:
    def __init__(self) -> None:
        self.cursor_instance = _Cursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_signal_repository_supports_managed_connection_factory() -> None:
    connections = []

    def connect():
        connection = _Connection()
        connections.append(connection)
        return connection

    signal_id = SignalRepository(connect).save_signal(
        {
            "symbol": "SBERP@MISX",
            "side": "BUY",
            "strategy": "VOLATILITY_BREAKOUT_EQUITY",
            "timeframe": "M5",
            "price": 100.0,
        }
    )

    assert signal_id
    assert len(connections) == 1
    assert connections[0].committed is True
    assert connections[0].closed is True
    assert len(connections[0].cursor_instance.executions) == 1


def test_runtime_reload_does_not_evict_base_symbols() -> None:
    service = object.__new__(RuntimeSymbolReloadService)
    service.source = "opportunity_scanner"
    service.sources = ["opportunity_scanner", "confirmation_universe"]
    service.limit = 10

    class _Provider:
        def load_symbols(self, **_kwargs):
            return ["BRQ6@RTSX"]

    service.provider = _Provider()
    decision = service.decide(["SBERP@MISX", "VTBR@MISX"])

    assert decision.active_symbols == ["SBERP@MISX", "VTBR@MISX", "BRQ6@RTSX"]
    assert decision.added_symbols == ["BRQ6@RTSX"]
    assert decision.removed_symbols == []


def test_equity_signal_is_persisted_and_sunday_contract_exists() -> None:
    pipeline = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    equity_route = pipeline[pipeline.index("def _process_equity_closed_bar_for_paper_signal") :]
    assert "repository.save_signal(intent)" in equity_route
    assert "persisted=1" in equity_route

    migration = (
        ROOT / "sql/analytics/132_sunday_market_session_contract_v1.sql"
    ).read_text()
    assert "MOEX_WEEKEND" in migration
    assert "'[7]'::jsonb" in migration
