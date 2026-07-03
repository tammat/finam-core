from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class EdgeValidationPipelinePage(Page):
    def __init__(self) -> None:
        super().__init__(route="/edge-validation-pipeline", title="Этапы", icon="▶", menu_order=17)

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-validation-use-market-universe?limit=50")
        rows = payload.get("data") or []

        body = ""
        for r in rows:
            body += f"""
            <tr>
                <td>{escape(str(r.get("validation_rank", "")))}</td>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("strategy", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("total_score"), 2))}</td>
                <td>{escape(str(r.get("research_priority", "")))}</td>
                <td>{escape(str(r.get("validation_status", "")))}</td>
                <td>{escape(str(r.get("recommended_action", "")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Этапы</h2>
            <p>Этапы проверки переключены на новую рыночную вселенную.</p>
            <p>Источник: marketcore_ui.edge_validation_use_market_universe_v1.</p>
        </section>

        <section class="card">
            <h2>Этапы проверки</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Стратегия</th>
                        <th>Score</th><th>Приоритет</th><th>Статус</th><th>Действие</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>
        """
