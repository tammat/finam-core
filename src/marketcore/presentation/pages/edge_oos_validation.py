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
        return "<p>OOS Validation пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("oos_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(str(row.get("oos_status", "")))}</td>
            <td>{escape(str(row.get("oos_readiness", "")))}</td>
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
                <th>OOS</th>
                <th>Readiness</th>
                <th>Score</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Trades</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeOosValidationPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-oos-validation",
            title="Edge OOS Validation",
            icon="✓",
            menu_order=19,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-oos-validation?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("oos_status") == "READY_FOR_OOS")
        wait_sample = sum(1 for row in rows if row.get("oos_status") == "WAIT_SAMPLE")
        observe = sum(1 for row in rows if row.get("oos_status") == "OBSERVE_MORE")
        blocked = sum(1 for row in rows if str(row.get("oos_status", "")).startswith("BLOCKED"))

        return f"""
        <section class="card">
            <h2>Edge OOS Validation</h2>
            <p>Out-of-sample readiness проверяет, можно ли кандидата передавать в OOS-контур.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_oos_validation_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready OOS", ctx.formatter.number(ready, 0))}
            {_metric("Observe", ctx.formatter.number(observe, 0))}
            {_metric("Wait Sample", ctx.formatter.number(wait_sample, 0))}
            {_metric("Blocked", ctx.formatter.number(blocked, 0))}
        </div>

        <section class="card">
            <h2>OOS Validation</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_OOS_BACKTEST_V1</p>
        </section>
        """
