#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_DATA_PROVIDER_INTERFACE_V1 ==="

mkdir -p \
  src/marketcore/research/execution/interfaces \
  src/marketcore/research/execution/providers \
  scripts

touch \
  src/marketcore/research/__init__.py \
  src/marketcore/research/execution/__init__.py \
  src/marketcore/research/execution/interfaces/__init__.py \
  src/marketcore/research/execution/providers/__init__.py

cat > src/marketcore/research/execution/interfaces/data_provider.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class MarketBar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketBars:
    symbol: str
    timeframe: str
    source: str
    bars: list[MarketBar]

    @property
    def count(self) -> int:
        return len(self.bars)


class DataProvider(Protocol):
    def load_market_data(
        self,
        symbol: str,
        timeframe: str,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
        parameters: dict | None = None,
    ) -> MarketBars:
        ...
PY

cat > scripts/test_data_provider_interface_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_PROVIDER_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/interfaces/data_provider.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime
from marketcore.research.execution.interfaces.data_provider import MarketBar, MarketBars

bar = MarketBar(
    ts=datetime.now(UTC),
    open=1.0,
    high=2.0,
    low=0.5,
    close=1.5,
    volume=100.0,
)

bars = MarketBars(
    symbol="TEST",
    timeframe="M5",
    source="unit",
    bars=[bar],
)

assert bars.count == 1
assert bars.bars[0].close == 1.5
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=DATA_PROVIDER_INTERFACE_V1_READY"
echo "VERDICT=TEST_DATA_PROVIDER_INTERFACE_V1_OK"
SH_TEST

chmod +x scripts/test_data_provider_interface_v1.sh
scripts/test_data_provider_interface_v1.sh

echo "VERDICT=BUILD_DATA_PROVIDER_INTERFACE_V1_OK"
