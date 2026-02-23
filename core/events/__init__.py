from dataclasses import dataclass
from typing import Any, Dict
from dataclasses import asdict

__all__ = [
    "StrategySignalEvent",
    "ExecutionEvent",
    "OrderCreateRequestedEvent",
    "RiskCheckRequestedEvent",
    "RiskApprovedEvent",
    "RiskRejectedEvent",
    "PortfolioUpdatedEvent",
]


@dataclass(frozen=True)
class StrategySignalEvent:
    symbol: str
    side: str
    qty: float
    price: float
    metadata: Dict[str, Any] | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionEvent:
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0
    fill_id: str | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OrderCreateRequestedEvent:
    symbol: str
    side: str
    qty: float
    price: float
    request_id: str | None = None
    metadata: Dict[str, Any] | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RiskCheckRequestedEvent:
    symbol: str
    side: str
    qty: float
    price: float
    request_id: str | None = None
    metadata: Dict[str, Any] | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RiskApprovedEvent:
    symbol: str
    side: str
    qty: float
    price: float
    request_id: str | None = None
    metadata: Dict[str, Any] | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RiskRejectedEvent:
    symbol: str
    side: str
    qty: float
    price: float
    reason: str
    request_id: str | None = None
    metadata: Dict[str, Any] | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioUpdatedEvent:
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    exposure: float
    drawdown: float
    metadata: Dict[str, Any] | None = None
    stream: str = "portfolio-1"

    @property
    def type(self) -> str:
        return self.__class__.__name__
    def to_dict(self) -> dict:
        return asdict(self)