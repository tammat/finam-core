from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.data.finam_marketdata_adapter import FinamMarketDataAdapter


def test_adapter_calls_stub_correctly():
    stub = MagicMock()
    adapter = FinamMarketDataAdapter(stub)

    start = datetime.now(timezone.utc)
    end = datetime.now(timezone.utc)

    adapter.get_bars(
        symbol="TEST@MISX",
        timeframe=1,
        start=start,
        end=end
    )

    assert stub.Bars.called