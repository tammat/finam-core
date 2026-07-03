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
        return "<p>Robustness Check пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("robustness_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(str(row.get("sample_size_status", "")))}</td>
            <td>{escape(str(row.get("pf_status", "")))}</td>
            <td>{escape(str(row.get("expectancy_status", "")))}</td>
            <td>{escape(str(row.get("winrate_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("robustness_score"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Robustness</th>
                <th>Sample</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>WinRate</th>
                <th>Score</th>
                <th>PF</th>
                <th>Exp.</th>
                <th>Trades</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeRobustnessCheckPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-robustness-check",
            title="Edge Robustness Check",
            icon="◇",
            menu_order=18,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-robustness-check?limit=50")
        rows = payload.get("data") or []

        wait_sample = sum(1 for row in rows if row.get("robustness_status") == "WAIT_SAMPLE")
        required = sum(1 for row in rows if row.get("robustness_status") == "ROBUSTNESS_REQUIRED")
        watchlist = sum(1 for row in rows if row.get("robustness_status") == "WATCHLIST")
        rejected = sum(1 for row in rows if row.get("robustness_status") == "ROBUSTNESS_REJECT")

        return f"""
        <section class="card">
            <h2>Edge Robustness Check</h2>
            <p>Проверка устойчивости кандидатов перед OOS и последующим продвижением.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_robustness_check_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Required", ctx.formatter.number(required, 0), "Готовы к robustness")}
            {_metric("Watchlist", ctx.formatter.number(watchlist, 0), "Наблюдать")}
            {_metric("Wait Sample", ctx.formatter.number(wait_sample, 0), "Копить выборку")}
            {_metric("Rejected", ctx.formatter.number(rejected, 0), "Не продвигать")}
        </div>

        <section class="card">
            <h2>Robustness Check</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_OOS_VALIDATION_V1</p>
        </section>
        """
