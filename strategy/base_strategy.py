# strategy/base_strategy.py

from abc import ABC, abstractmethod
from typing import List
from strategy.signal import Signal


class BaseStrategy(ABC):
    @abstractmethod
    def generate(self) -> List[Signal]:
        """Вернуть список сигналов (может быть пустым)."""
        raise NotImplementedError