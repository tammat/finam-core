# storage/base_storage.py

from abc import ABC, abstractmethod
from typing import Iterable

class BaseStorage(ABC):

    @abstractmethod
    def append_fill(self, fill):
        pass

    @abstractmethod
    def load_fills(self, symbol: str | None = None) -> Iterable:
        pass