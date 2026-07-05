from __future__ import annotations

import traceback

from marketcore.presentation.layout import render_layout
from marketcore.presentation.pages.edge_audit_page import render_edge_audit_page


def route(path: str) -> tuple[int, bytes]:
    if path in ("/edge-audit", "/edge-audit/"):
        return 200, render_edge_audit_page()

    try:
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
