# execution/execution_engine.py

from abc import ABC, abstractmethod
from execution.order_model import Order
from core.events import FillEvent
from datetime import datetime


class ExecutionEngine(ABC):

    @abstractmethod
    def execute(self, order: Order, market_price: float, ts: datetime) -> list[FillEvent]:
        pass