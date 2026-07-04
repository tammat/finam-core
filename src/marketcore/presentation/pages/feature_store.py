from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class FeatureStorePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/feature-store",
            title="Feature Store",
            icon="∑",
            menu_order=35,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/feature-store/summary").get("data") or {}
        health = ctx.api_get("/api/kg/v1/feature-store/health").get("data") or {}
        rows = ctx.api_get("/api/kg/v1/feature-store").get("data") or []

        body = ""
        for r in rows[:100]:
            body += f"""
            <tr>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("bar_ts", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("close"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("return1_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("return5_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("range_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("body_pct"), 4))}</td>
                <td>{escape(ctx.formatter.number(r.get("feature_quality_score"), 4))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Feature Store</h2>
            <p>Единый слой признаков. Источник: Platform API → analytics.feature_snapshot_v1.</p>
            <p>Health: {escape(str(health.get("health_status", "")))} · Timer: {escape(str(health.get("timer_active", "")))}</p>
            <p>Последний бар: {escape(str(summary.get("latest_bar_ts", "")))} · Обновлено: {escape(str(summary.get("refreshed_at", "")))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>Всего признаков</h3><p>{escape(str(summary.get("feature_rows", "")))}</p></div>
            <div class="card"><h3>Инструментов</h3><p>{escape(str(summary.get("feature_symbols", "")))}</p></div>
            <div class="card"><h3>Среднее качество</h3><p>{escape(ctx.formatter.number(summary.get("avg_quality_score"), 4))}</p></div>
            <div class="card"><h3>Return1</h3><p>{escape(str(summary.get("with_return1", "")))}</p></div>
            <div class="card"><h3>Volume Ratio20</h3><p>{escape(str(summary.get("with_volume_ratio20", "")))}</p></div>
            <div class="card"><h3>Health</h3><p>{escape(str(health.get("health_status", "")))}</p></div>
        </section>

        <section class="card">
            <h2>Последние признаки</h2>
            <table>
                <thead>
                    <tr>
                        <th>Инструмент</th>
                        <th>TF</th>
                        <th>Бар</th>
                        <th>Close</th>
                        <th>Return1 %</th>
                        <th>Return5 %</th>
                        <th>Range %</th>
                        <th>Body %</th>
                        <th>Quality</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующий этап</h2>
            <p>FEATURE_STORE_DASHBOARD_V1</p>
        </section>
        """
