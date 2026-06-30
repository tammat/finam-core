from __future__ import annotations

from typing import Any


def flat_print(row: dict[str, Any]) -> None:
    for key, value in row.items():
        print(f"{key}={value}")


def flat_print_rows(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        flat_print(row)
