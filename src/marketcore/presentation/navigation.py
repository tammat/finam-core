from __future__ import annotations

from html import escape

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.ui_labels import display_label


def render_navigation(active_route: str) -> str:
    items: list[str] = []

    for page in menu_pages():
        active = " active" if page.route == active_route else ""
        label = display_label(page.route, page.title)

        items.append(
            f'<a class="nav-item{active}" href="{escape(page.route)}">'
            f'<span class="nav-icon">{escape(page.icon)}</span>'
            f'<span class="nav-label">{escape(label)}</span>'
            f'</a>'
        )

    return "\n".join(items)
