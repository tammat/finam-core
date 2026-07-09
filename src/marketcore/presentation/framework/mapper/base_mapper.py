from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class BaseMapper(ABC):
    @classmethod
    @abstractmethod
    def from_db(cls, row: Any) -> Any:
        raise NotImplementedError

    @classmethod
    def from_rows(cls, rows: Iterable[Any]) -> list[Any]:
        return [cls.from_db(row) for row in rows]
