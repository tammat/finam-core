from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class MarketUniverseResearchQueuePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/market-universe-research-queue",
            title="Очередь исследований",
            icon="→",
            menu_order=25,
        )

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
                <td>{escape(str(r.get("research_status", "")))}</td>
                <td>{escape(str(r.get("recommended_action", "")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Очередь исследований</h2>
            <p>TOP-инструменты из Market Universe Ranking для запуска Research / Edge Discovery.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.market_universe_research_queue_v1.</p>
        </section>

        <section class="card">
            <h2>Research Queue</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Asset</th>
                        <th>Score</th><th>Priority</th><th>Strategy Family</th>
                        <th>Status</th><th>Действие</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующее действие</h2>
            <p>MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1</p>
        </section>
        """
