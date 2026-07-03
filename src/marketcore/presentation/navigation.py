from __future__ import annotations

from collections import defaultdict
from html import escape

from marketcore.presentation.registry import menu_pages
from marketcore.presentation.route_groups import OTHER_GROUP, group_for_route, route_groups
from marketcore.presentation.ui_labels import display_label


def render_navigation(active_route: str) -> str:
    pages_by_group = defaultdict(list)

    for page in menu_pages():
        group = group_for_route(page.route)
        pages_by_group[group.key].append(page)

    chunks: list[str] = []

    for group in (*route_groups(), OTHER_GROUP):
        pages = pages_by_group.get(group.key, [])
        if not pages:
            continue

        chunks.append('<div class="nav-group">')
        chunks.append(f'<div class="nav-group-title">{escape(group.title_ru)}</div>')

        for page in sorted(pages, key=lambda p: p.menu_order):
            active = " active" if page.route == active_route else ""
            label = display_label(page.route, page.title)

            chunks.append(
                f'<a class="nav-item{active}" href="{escape(page.route)}">'
                f'<span class="nav-icon">{escape(page.icon)}</span>'
                f'<span class="nav-label">{escape(label)}</span>'
                f'</a>'
            )

        chunks.append("</div>")

    return "\n".join(chunks)
