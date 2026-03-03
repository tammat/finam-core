from dataclasses import dataclass
from typing import Literal, Optional, Dict


Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class SignalIntent:
    symbol: str
    side: Side
    quantity: float
    strategy_id: Optional[str] = None
    meta: Optional[Dict] = None