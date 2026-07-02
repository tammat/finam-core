from __future__ import annotations

from html import escape

from marketcore.presentation.registry import menu_pages


def render_navigation(active_route: str) -> str:
    items = []
    for page in menu_pages():
        active = " active" if page.route == active_route else ""
        items.append(
            f'<a class="nav-item{active}" href="{escape(page.route)}">'
            f'<span>{escape(page.icon)}</span> {escape(page.title)}</a>'
        )
    return "\n".join(items)
