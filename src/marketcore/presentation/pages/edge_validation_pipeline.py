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
        return "<p>Pipeline пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("pipeline_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("pipeline_status", "")))}</td>
            <td>{escape(str(row.get("sample_check_status", "")))}</td>
            <td>{escape(str(row.get("pf_check_status", "")))}</td>
            <td>{escape(str(row.get("expectancy_check_status", "")))}</td>
            <td>{escape(str(row.get("robustness_status", "")))}</td>
            <td>{escape(str(row.get("oos_status", "")))}</td>
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
                <th>Pipeline</th>
                <th>Sample</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Robustness</th>
                <th>OOS</th>
                <th>PF</th>
                <th>Exp.</th>
                <th>Trades</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class EdgeValidationPipelinePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-validation-pipeline",
            title="Edge Validation Pipeline",
            icon="▶",
            menu_order=17,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-validation-pipeline?limit=50")
        rows = payload.get("data") or []

        accumulate = sum(1 for row in rows if row.get("pipeline_status") == "ACCUMULATE_SAMPLE")
        ready = sum(1 for row in rows if row.get("pipeline_status") == "READY_FOR_ROBUSTNESS")
        observe = sum(1 for row in rows if row.get("pipeline_status") == "OBSERVE_MORE")
        rejected = sum(1 for row in rows if row.get("pipeline_status") == "REJECTED_BY_RULES")

        return f"""
        <section class="card">
            <h2>Edge Validation Pipeline</h2>
            <p>Pipeline переводит кандидатов из Edge Validation Queue в формальные статусы проверки.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.edge_validation_pipeline_v1.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего", ctx.formatter.number(len(rows), 0))}
            {_metric("Ready", ctx.formatter.number(ready, 0), "Готовы к robustness")}
            {_metric("Observe", ctx.formatter.number(observe, 0), "Требуют наблюдения")}
            {_metric("Sample", ctx.formatter.number(accumulate, 0), "Накопить выборку")}
            {_metric("Rejected", ctx.formatter.number(rejected, 0), "Не продвигать")}
        </div>

        <section class="card">
            <h2>Pipeline</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>EDGE_ROBUSTNESS_CHECK_V1</p>
        </section>
        """
