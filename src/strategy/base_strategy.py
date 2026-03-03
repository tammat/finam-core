from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class Signal:
    symbol: str
    side: str  # "LONG" | "SHORT"
    entry: float
    stop: float
    take: float
    reason: str


class BaseStrategy(ABC):

    def __init__(self, symbol: str):
        self.symbol = symbol

    @abstractmethod
    def on_bar(self, bar) -> Optional[Signal]:
        """
        Called on each new closed bar.
        Must return Signal or None.
        """
        pass