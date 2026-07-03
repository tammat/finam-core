from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
    """


def _table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Матрица маршрутов пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("group_title_ru", "")))}</td>
            <td><a href="{escape(str(row.get("route", "")))}">{escape(str(row.get("label_ru", "")))}</a></td>
            <td>{escape(str(row.get("route", "")))}</td>
            <td>{escape(str(row.get("http_status", "")))}</td>
            <td>{escape(str(row.get("http_ok", "")))}</td>
            <td>{escape(str(row.get("contains_shell_marker", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("content_length"), 0))}</td>
            <td>{escape(str(row.get("issue", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>Группа</th>
                <th>Страница</th>
                <th>Route</th>
                <th>HTTP</th>
                <th>OK</th>
                <th>Shell</th>
                <th>Размер</th>
                <th>Проблема</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class MarketcoreUiRouteHealthMatrixPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/marketcore-ui-route-health-matrix",
            title="Матрица здоровья маршрутов UI",
            icon="✓",
            menu_order=122,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/marketcore-ui-route-health-matrix")
        rows = payload.get("data") or []

        ok_rows = sum(1 for row in rows if row.get("http_ok") is True)
        bad_rows = len(rows) - ok_rows

        return f"""
        <section class="card">
            <h2>Матрица здоровья маршрутов UI</h2>
            <p>Проверяет, какие страницы MarketCore UI Shell на 8080 реально открываются и содержат shell marker.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.marketcore_ui_route_health_matrix_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;">
            {_metric("Всего маршрутов", ctx.formatter.number(len(rows), 0))}
            {_metric("OK", ctx.formatter.number(ok_rows, 0))}
            {_metric("Проблемы", ctx.formatter.number(bad_rows, 0))}
        </div>

        <section class="card">
            <h2>Маршруты</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Комментарий по рыночным данным</h2>
            <p>Текущий Paper Edge Discovery показывает paper/research-кандидатов. Свежие market data ещё не подключены к этому экрану как отдельный feed.</p>
            <p>Следующий необходимый шаг: PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1.</p>
        </section>
        """
