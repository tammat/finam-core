from __future__ import annotations
from html import escape

def h(value) -> str:
    return escape(str(value if value is not None else ""))
