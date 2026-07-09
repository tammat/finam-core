from __future__ import annotations

from typing import Any


class HomeStatusScalarMapperV1:
    @staticmethod
    def bool_value(row: Any, column_name: str) -> bool:
        return bool(row[column_name])

    @staticmethod
    def int_value(row: Any, column_name: str) -> int:
        return int(row[column_name] or 0)
