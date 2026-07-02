from __future__ import annotations

from marketcore.presentation.layout import render_layout
from marketcore.presentation.registry import get_page


def route(path: str) -> tuple[int, bytes]:
    page = get_page(path)
    if page is None:
        return 404, render_layout(
            title="404",
            active_route="",
            content='<section class="card"><h2>Страница не найдена</h2></section>',
        )

    return 200, render_layout(
        title=page.title,
        active_route=page.route,
        content=page.render(),
    )
