from __future__ import annotations

from html import escape

from marketcore.presentation.api_client import get_json
from marketcore.presentation.page import Page


def _table(rows: list[dict], columns: list[str]) -> str:
    if not rows:
        return "<p>Нет данных.</p>"
    head = "".join(f"<th>{escape(c)}</th>" for c in columns)
    body = ""
    for row in rows:
        body += "<tr>" + "".join(
            f"<td>{escape(str(row.get(c, '')))}</td>" for c in columns
        ) + "</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


class KnowledgeGraphPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/knowledge-graph",
            title="Knowledge Graph",
            icon="◎",
            menu_order=30,
        )

    def render(self) -> str:
        stats = get_json("/api/kg/v1/statistics")
        validation = get_json("/api/kg/v1/validation")
        search = get_json("/api/kg/v1/search?q=сделки&locale=ru")

        stats_rows = stats.get("data") or []
        validation_rows = validation.get("data") or []
        search_rows = (search.get("data") or {}).get("terms") or []

        return f"""
        <section class="card">
            <h2>Knowledge Graph</h2>
            <p>Страница подключена через MarketCore UI Shell и читает данные только через Knowledge Graph API.</p>
        </section>

        <section class="card">
            <h2>Статистика</h2>
            {_table(stats_rows, ["domain", "nodes", "edges", "entity_types", "edge_types"])}
        </section>

        <section class="card">
            <h2>Валидация</h2>
            {_table(validation_rows, ["domain", "status", "total_findings", "finished_at"])}
        </section>

        <section class="card">
            <h2>Семантический поиск: сделки</h2>
            {_table(search_rows, ["locale", "raw_term", "object_type", "object_key", "match_type", "confidence"])}
        </section>
        """
