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
        return "<p>Micro Live Readiness пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("readiness_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("readiness_status", "")))}</td>
            <td>{escape(str(row.get("micro_live_ready", "")))}</td>
            <td>{escape(str(row.get("micro_live_allowed", "")))}</td>
            <td>{escape(str(row.get("backtest_status", "")))}</td>
            <td>{escape(str(row.get("oos_status", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("total_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("oos_expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("stability_score"), 4))}</td>
            <td>{escape(str(row.get("block_reason", "")))}</td>
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
                <th>Readiness</th>
                <th>Ready</th>
                <th>Allowed</th>
                <th>Backtest</th>
                <th>OOS</th>
                <th>Robustness</th>
                <th>Total</th>
                <th>OOS Trades</th>
                <th>OOS PF</th>
                <th>OOS Exp.</th>
                <th>Stability</th>
                <th>Block Reason</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class MicroLiveReadinessPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/micro-live-readiness",
            title="Micro Live Readiness",
            icon="▶",
            menu_order=21,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/micro-live-readiness?limit=50")
        rows = payload.get("data") or []

        ready = sum(1 for row in rows if row.get("micro_live_ready") is True)
        allowed = sum(1 for row in rows if row.get("micro_live_allowed") is True)
        wait_sample = sum(1 for row in rows if row.get("readiness_status") in {"WAIT_SAMPLE", "WAIT_OOS_SAMPLE"})
        blocked = sum(1 for row in rows if str(row.get("readiness_status", "")).startswith("BLOCKED"))

        return f"""
        <section class="card">
            <h2>Micro Live Readiness</h2>
            <p>Финальный шлюз допуска кандидата к Micro Live. Автоматическое включение исполнения запрещено.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.micro_live_readiness_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready", ctx.formatter.number(ready, 0), "Готовы к risk review")}
            {_metric("Allowed", ctx.formatter.number(allowed, 0), "Должно быть 0")}
            {_metric("Wait Sample", ctx.formatter.number(wait_sample, 0))}
            {_metric("Blocked", ctx.formatter.number(blocked, 0))}
        </div>

        <section class="card">
            <h2>Readiness Gate</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>PAPER_EDGE_DISCOVERY_PHASE_ACCEPTANCE_V1</p>
        </section>
        """
