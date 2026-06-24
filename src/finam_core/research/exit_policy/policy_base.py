from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ClosedTradeInput:
    trade_id: str
    symbol: str
    entry_ts: datetime
    exit_ts: datetime
    entry_price: float
    exit_price: float
    net_pnl: float
    commission: float


@dataclass(frozen=True)
class VirtualExitResult:
    policy_name: str
    trade_id: str
    virtual_exit_ts: datetime
    virtual_exit_price: float
    virtual_net_pnl: float
    reason: str


class ExitPolicy:
    name = "BASE_EXIT_POLICY"

    def simulate(self, trade: ClosedTradeInput) -> VirtualExitResult:
        raise NotImplementedError
