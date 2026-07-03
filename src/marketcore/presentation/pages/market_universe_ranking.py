from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class MarketUniverseRankingPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/market-universe-ranking",
            title="Рейтинг рыночной вселенной",
            icon="★",
            menu_order=24,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/market-universe-ranking?limit=100")
        rows = payload.get("data") or []

        body = ""
        for r in rows:
            body += f"""
            <tr>
                <td>{escape(str(r.get("rank", "")))}</td>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("asset_class", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("total_score"), 2))}</td>
                <td>{escape(ctx.formatter.number(r.get("freshness_score"), 1))}</td>
                <td>{escape(ctx.formatter.number(r.get("history_score"), 1))}</td>
                <td>{escape(ctx.formatter.number(r.get("liquidity_score"), 1))}</td>
                <td>{escape(str(r.get("ranking_status", "")))}</td>
                <td>{escape(str(r.get("recommended_action", "")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Рейтинг рыночной вселенной</h2>
            <p>Единый рейтинг инструментов для Research / Edge Discovery.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.market_universe_ranking_v1.</p>
        </section>

        <section class="card">
            <h2>TOP Universe</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Asset</th>
                        <th>Total</th><th>Fresh</th><th>History</th><th>Liquidity</th>
                        <th>Status</th><th>Действие</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующее действие</h2>
            <p>MARKET_UNIVERSE_RESEARCH_QUEUE_V1</p>
        </section>
        """
