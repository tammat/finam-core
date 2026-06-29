from __future__ import annotations

from html import escape
from typing import Any


def registry_card(title: str, value: Any) -> str:
    return f'<div class="card"><b>{escape(str(title))}</b>: {escape(str(value))}</div>'


def registry_policy_block(policy: str) -> str:
    return f"<p>registry_policy={escape(policy)}</p>"
