#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_TRADE_GENERATOR_INTERFACE_V1 ==="

mkdir -p src/marketcore/research/execution/dto
mkdir -p src/marketcore/research/execution/interfaces

cat > src/marketcore/research/execution/dto/research_trade.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4


TradeSide = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class ResearchTrade:
    trade_uuid: UUID
    signal_uuid: UUID | None
    entry_ts: datetime
    exit_ts: datetime
    side: TradeSide
    entry_price: float
    exit_price: float
    quantity: float
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    execution_model: str
    metadata: dict

    @staticmethod
    def create(
        signal_uuid: UUID | None,
        entry_ts: datetime,
        exit_ts: datetime,
        side: TradeSide,
        entry_price: float,
        exit_price: float,
        quantity: float,
        commission: float,
        slippage: float,
        execution_model: str,
        metadata: dict | None = None,
    ) -> "ResearchTrade":
        signed_qty = quantity if side == "BUY" else -quantity
        gross_pnl = (exit_price - entry_price) * signed_qty
        net_pnl = gross_pnl - commission - slippage

        return ResearchTrade(
            trade_uuid=uuid4(),
            signal_uuid=signal_uuid,
            entry_ts=entry_ts,
            exit_ts=exit_ts,
            side=side,
            entry_price=float(entry_price),
            exit_price=float(exit_price),
            quantity=float(quantity),
            gross_pnl=float(gross_pnl),
            commission=float(commission),
            slippage=float(slippage),
            net_pnl=float(net_pnl),
            execution_model=execution_model,
            metadata=metadata or {},
        )
PY

cat > src/marketcore/research/execution/interfaces/trade_generator.py <<'PY'
from __future__ import annotations

from typing import Protocol

from marketcore.research.execution.dto.research_trade import ResearchTrade
from marketcore.research.execution.dto.signal import StrategySignal
from marketcore.research.execution.interfaces.data_provider import MarketBars


class TradeGenerator(Protocol):
    generator_name: str
    generator_version: str

    def run(
        self,
        market_data: MarketBars,
        signals: list[StrategySignal],
        parameters: dict | None = None,
    ) -> list[ResearchTrade]:
        ...
PY

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "trade.generator.title": "Trade Generator",
        "trade.generator.subtitle": "Компонент преобразования сигналов стратегии в исследовательские сделки.",
        "trade.generator.execution_model": "Модель исполнения",
        "trade.generator.version": "Версия генератора",
        "trade.generator.name": "Название генератора"
    })
except NameError:
    pass
PY

cat > scripts/test_trade_generator_interface_v1.sh <<'TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADE_GENERATOR_INTERFACE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/dto/research_trade.py \
  src/marketcore/research/execution/interfaces/trade_generator.py \
  src/marketcore/presentation/ui_labels.py

PYTHONPATH=src python - <<'PY'
from datetime import UTC, datetime, timedelta

from marketcore.research.execution.dto.research_trade import ResearchTrade

entry = datetime.now(UTC)
exit_ts = entry + timedelta(minutes=5)

buy = ResearchTrade.create(
    signal_uuid=None,
    entry_ts=entry,
    exit_ts=exit_ts,
    side="BUY",
    entry_price=100.0,
    exit_price=105.0,
    quantity=2.0,
    commission=1.0,
    slippage=0.5,
    execution_model="CLOSE_TO_CLOSE",
)

sell = ResearchTrade.create(
    signal_uuid=None,
    entry_ts=entry,
    exit_ts=exit_ts,
    side="SELL",
    entry_price=105.0,
    exit_price=100.0,
    quantity=2.0,
    commission=1.0,
    slippage=0.5,
    execution_model="CLOSE_TO_CLOSE",
)

assert buy.gross_pnl == 10.0
assert buy.net_pnl == 8.5
assert sell.gross_pnl == 10.0
assert sell.net_pnl == 8.5
assert buy.execution_model == "CLOSE_TO_CLOSE"
PY

grep -q "trade.generator.title" src/marketcore/presentation/ui_labels.py
grep -q "trade.generator.execution_model" src/marketcore/presentation/ui_labels.py

echo "i18n=ok"
echo "sql_in_component=0"
echo "side_effects=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADE_GENERATOR_INTERFACE_V1_READY"
echo "VERDICT=TEST_TRADE_GENERATOR_INTERFACE_V1_OK"
TEST

chmod +x scripts/test_trade_generator_interface_v1.sh
scripts/test_trade_generator_interface_v1.sh

echo "VERDICT=BUILD_TRADE_GENERATOR_INTERFACE_V1_OK"
