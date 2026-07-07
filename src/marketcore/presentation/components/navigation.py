from __future__ import annotations

from marketcore.presentation.components.html import h
from marketcore.presentation.navigation import NavigationGroup


def render_navigation(groups: list[NavigationGroup], current_route: str = "/") -> str:
    html = ['<nav class="workspace-nav">']

    for group in groups:
        html.append(
            f'<div class="workspace-nav-group">'
            f'<div class="workspace-nav-group-title">{h(group.icon)} {h(group.caption)}</div>'
        )

        for item in group.items:
            active = " active" if item.route == current_route else ""
            html.append(
                f'<a class="workspace-nav-item{active}" href="{h(item.route)}">'
                f'<span class="workspace-nav-icon">{h(item.icon)}</span>'
                f'<span class="workspace-nav-caption">{h(item.caption)}</span>'
                f'</a>'
            )

        html.append("</div>")

    html.append("</nav>")
    return "".join(html)
