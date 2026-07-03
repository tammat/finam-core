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
        return "<p>OOS Backtest пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("backtest_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("backtest_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("in_sample_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("in_sample_profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("in_sample_expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("stability_score"), 4))}</td>
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
                <th>Backtest</th>
                <th>Total</th>
                <th>IS</th>
                <th>OOS</th>
                <th>IS PF</th>
                <th>OOS PF</th>
                <th>IS Exp.</th>
                <th>OOS Exp.</th>
                <th>Stability</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeOosBacktestPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-oos-backtest",
            title="Edge OOS Backtest",
            icon="✓",
            menu_order=20,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-oos-backtest?limit=50")
        rows = payload.get("data") or []

        passed = sum(1 for row in rows if row.get("backtest_status") == "OOS_PASS")
        wait = sum(1 for row in rows if str(row.get("backtest_status", "")).startswith("WAIT"))
        failed = sum(1 for row in rows if row.get("backtest_status") == "OOS_FAIL")
        not_ready = sum(1 for row in rows if row.get("backtest_status") == "NOT_READY_FROM_OOS_GATE")

        return f"""
        <section class="card">
            <h2>Edge OOS Backtest</h2>
            <p>Temporal split validation: in-sample 70% и OOS 30% по закрытым paper-сделкам.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_oos_backtest_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("OOS Pass", ctx.formatter.number(passed, 0))}
            {_metric("Wait", ctx.formatter.number(wait, 0))}
            {_metric("Not Ready", ctx.formatter.number(not_ready, 0))}
            {_metric("Failed", ctx.formatter.number(failed, 0))}
        </div>

        <section class="card">
            <h2>OOS Backtest</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>MICRO_LIVE_READINESS_V1</p>
        </section>
        """
