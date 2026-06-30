from __future__ import annotations

from html import escape
from typing import Any


def event_card(title: str, value: Any) -> str:
    return f'<div class="card"><b>{escape(str(title))}</b>: {escape(str(value))}</div>'


def event_policy_block(policy: str) -> str:
    return f"<p>event_policy={escape(policy)}</p>"
