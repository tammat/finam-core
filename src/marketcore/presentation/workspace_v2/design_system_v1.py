from __future__ import annotations

from html import escape
from decimal import Decimal
from typing import Any


def _safe(value: Any) -> str:
    return escape(str(value if value is not None else "—"))


def render_badge(label: str, status: str) -> str:
    css = {
        "PASS": "mc-v2-badge-ok",
        "OK": "mc-v2-badge-ok",
        "WARNING": "mc-v2-badge-warning",
        "BLOCKED": "mc-v2-badge-blocked",
        "LOCKED": "mc-v2-badge-locked",
    }.get(str(status).upper(), "mc-v2-badge-locked")
    return f'<span class="mc-v2-badge {css}">{_safe(label)}</span>'


def render_progress(value: Any, label: str = "") -> str:
    try:
        pct = max(Decimal("0"), min(Decimal("100"), Decimal(str(value or 0))))
    except Exception:
        pct = Decimal("0")
    return (
        '<div class="mc-v2-progress"'
        + (f' aria-label="{_safe(label)}"' if label else "")
        + f'><div class="mc-v2-progress-fill" style="width:{pct}%"></div></div>'
    )


def render_kpi_card(label: str, value: Any, status: str = "", hint: str = "") -> str:
    badge = render_badge(status, status) if status else ""
    return (
        '<section class="mc-v2-card mc-v2-kpi">'
        f'<div class="mc-v2-kpi-label">{_safe(label)}</div>'
        f'<div class="mc-v2-kpi-value">{_safe(value)}</div>'
        f'{badge}'
        f'<div class="mc-v2-kpi-label">{_safe(hint)}</div>'
        '</section>'
    )


def render_action_card(title: str, body: str, action_label: str, href: str) -> str:
    return (
        '<section class="mc-v2-card">'
        f'<h3>{_safe(title)}</h3>'
        f'<p>{_safe(body)}</p>'
        f'<a class="mc-v2-button" href="{_safe(href)}">{_safe(action_label)}</a>'
        '</section>'
    )

def render_kpi_card_v2(label: str, value: Any, status_code: str = "", status_label: str = "", hint: str = "") -> str:
    badge = render_badge(status_label, status_code) if status_code else ""
    return (
        '<section class="mc-v2-card mc-v2-kpi">'
        f'<div class="mc-v2-kpi-label">{_safe(label)}</div>'
        f'<div class="mc-v2-kpi-value">{_safe(value)}</div>'
        f'{badge}'
        f'<div class="mc-v2-kpi-label">{_safe(hint)}</div>'
        '</section>'
    )
