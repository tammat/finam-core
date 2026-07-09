from __future__ import annotations

import traceback


from marketcore.presentation.layout import render_layout
from marketcore.presentation.workspace_v2.home_v1 import (
    render_workspace_v2_home_v1,
)
from marketcore.presentation.workspace_v2.portfolio_v1 import (
    render_workspace_v2_portfolio_v1,
)



def route(path: str) -> tuple[int, bytes]:
    try:

        if path in ("/workspace-v2", "/workspace-v2/"):
            return (
                200,
                render_workspace_v2_home_v1().encode("utf-8"),
            )

        if path in ("/workspace-v2/portfolio", "/workspace-v2/portfolio/"):
            return (
                200,
                render_workspace_v2_portfolio_v1().encode("utf-8"),
            )

        from marketcore.presentation.registry import get_page

        page = get_page(path)
    except Exception as exc:
        content = (
            '<section class="card">'
            '<h2>Ошибка маршрутизации</h2>'
            f'<pre>{type(exc).__name__}: {exc}</pre>'
            f'<pre>{traceback.format_exc()}</pre>'
            '</section>'
        )
        return 500, render_layout(
            title="Ошибка маршрутизации",
            active_route="",
            content=content,
        )

    if page is None:
        return 404, render_layout(
            title="404",
            active_route="",
            content='<section class="card"><h2>Страница не найдена</h2></section>',
        )

    try:
        content = page.render()
    except Exception as exc:
        content = (
            '<section class="card">'
            '<h2>Ошибка рендера страницы</h2>'
            f'<pre>{type(exc).__name__}: {exc}</pre>'
            f'<pre>{traceback.format_exc()}</pre>'
            '</section>'
        )
        return 500, render_layout(
            title="Ошибка рендера",
            active_route=page.route,
            content=content,
        )

    return 200, render_layout(
        title=page.title,
        active_route=page.route,
        content=content,
    )
