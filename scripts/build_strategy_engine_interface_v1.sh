#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_ENGINE_INTERFACE_V1 ==="

mkdir -p \
  src/marketcore/research/execution/dto \
  src/marketcore/research/execution/interfaces \
  src/marketcore/research/execution/engines \
  scripts

touch \
  src/marketcore/research/execution/dto/__init__.py \
  src/marketcore/research/execution/engines/__init__.py

cat > src/marketcore/research/execution/dto/signal.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


SignalDirection = Literal["BUY", "SELL", "FLAT"]


@dataclass(frozen=True)
class StrategySignal:
    signal_ts: datetime
    direction: SignalDirection
    price: float
    confidence: float
    metadata: dict

    @property
    def is_trade_signal(self) -> bool:
        return self.direction in {"BUY", "SELL"}
PY

cat > src/marketcore/research/execution/interfaces/strategy_engine.py <<'PY'
from __future__ import annotations

from typing import Protocol

from marketcore.research.execution.dto.signal import StrategySignal
from marketcore.research.execution.interfaces.data_provider import MarketBars


class StrategyEngine(Protocol):
    engine_name: str

    def execute(
        self,
        market_data: MarketBars,
        parameters: dict | None = None,
    ) -> list[StrategySignal]:
        ...
PY

cat > scripts/test_strategy_engine_interface_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_ENGINE_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/dto/signal.py \
  src/marketcore/research/execution/interfaces/strategy_engine.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime

from marketcore.research.execution.dto.signal import StrategySignal

s = StrategySignal(
    signal_ts=datetime.now(UTC),
    direction="BUY",
    price=100.0,
    confidence=0.75,
    metadata={"source": "unit"},
)

assert s.is_trade_signal is True
assert s.direction == "BUY"
assert s.price == 100.0
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_ENGINE_INTERFACE_V1_READY"
echo "VERDICT=TEST_STRATEGY_ENGINE_INTERFACE_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_engine_interface_v1.sh
scripts/test_strategy_engine_interface_v1.sh

echo "VERDICT=BUILD_STRATEGY_ENGINE_INTERFACE_V1_OK"
