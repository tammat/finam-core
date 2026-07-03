from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class EdgeValidationQueuePage(Page):
    def __init__(self) -> None:
        super().__init__(route="/edge-validation-queue", title="Проверка", icon="✓", menu_order=16)

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/market-universe-research-queue?limit=50")
        rows = payload.get("data") or []

        body = ""
        for r in rows:
            body += f"""
            <tr>
                <td>{escape(str(r.get("queue_rank", "")))}</td>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("asset_class", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("total_score"), 2))}</td>
                <td>{escape(str(r.get("research_priority", "")))}</td>
                <td>{escape(str(r.get("recommended_strategy_family", "")))}</td>
                <td>Ожидает проверки</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Проверка</h2>
            <p>Очередь кандидатов теперь строится из Market Universe Research Queue, а не из старого BR-only источника.</p>
            <p>Источник: marketcore_ui.market_universe_research_queue_v1.</p>
        </section>

        <section class="card">
            <h2>Кандидаты</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Класс</th>
                        <th>Score</th><th>Приоритет</th><th>Стратегия</th><th>Статус</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующее действие</h2>
            <p>EDGE_PIPELINE_USE_MARKET_UNIVERSE_V1</p>
        </section>
        """
