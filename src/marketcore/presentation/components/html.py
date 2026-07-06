from __future__ import annotations

from html import escape


def h(value: object) -> str:
    return escape("" if value is None else str(value))
