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


def _row(label: str, value: str) -> str:
    return f"""
    <tr>
        <td>{escape(label)}</td>
        <td>{escape(value)}</td>
    </tr>
    """


def _candidate_table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Кандидаты Research пока не найдены.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("candidate_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("side", "")))}</td>
            <td>{escape(str(row.get("candidate_status", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.percent(row.get("winrate"), 2))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
            <td>{escape(ctx.formatter.number(row.get("net_pnl"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("score"), 4))}</td>
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
                <th>Side</th>
                <th>Статус</th>
                <th>Expectancy</th>
                <th>PF</th>
                <th>WinRate</th>
                <th>Trades</th>
                <th>Net PnL</th>
                <th>Score</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


def _candidate_detail_table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Нет данных для детализации TOP кандидатов.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("candidate_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("profit_factor"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("expectancy"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("trades"), 0))}</td>
            <td>{escape(str(row.get("detail_status", "")))}</td>
            <td>{escape(str(row.get("next_step", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Инструмент</th>
                <th>Стратегия</th>
                <th>PF</th>
                <th>Expectancy</th>
                <th>Trades</th>
                <th>Детальный статус</th>
                <th>Следующий шаг</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


def _candidate_explainability_table(rows: list[dict], ctx) -> str:
    if not rows:
        return "<p>Нет данных объяснимости кандидатов.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("candidate_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("explainability_status", "")))}</td>
            <td>{escape(str(row.get("why_selected", "")))}</td>
            <td>{escape(str(row.get("evidence_summary", "")))}</td>
            <td>{escape(str(row.get("risk_explanation", "")))}</td>
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
                <th>Статус объяснения</th>
                <th>Почему выбран</th>
                <th>Доказательства</th>
                <th>Риски</th>
                <th>Рекомендация</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeDiscoveryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-discovery",
            title="Paper Edge Discovery",
            icon="◇",
            menu_order=15,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        discovery = ctx.api_get("/api/kg/v1/paper-edge-discovery")
        candidates_payload = ctx.api_get("/api/kg/v1/paper-edge-research-candidates?limit=20")
        detail_payload = ctx.api_get("/api/kg/v1/paper-edge-top-candidates-detail?limit=10")
        explain_payload = ctx.api_get("/api/kg/v1/paper-edge-candidate-explainability?limit=10")

        data = discovery.get("data") or {}
        paper = data.get("paper_runtime") or {}
        kg = data.get("knowledge_graph") or {}
        validation = data.get("validation") or {}
        candidates = candidates_payload.get("data") or []
        details = detail_payload.get("data") or []
        explanations = explain_payload.get("data") or []

        paper_status = str(paper.get("paper_status", "UNKNOWN"))
        validation_status = str(validation.get("status", "UNKNOWN"))

        closed_total = ctx.formatter.number(paper.get("closed_trades_total"), 0)
        closed_today = ctx.formatter.number(paper.get("closed_trades_today"), 0)
        signals_today = ctx.formatter.number(paper.get("signals_today"), 0)
        fills_today = ctx.formatter.number(paper.get("fills_today"), 0)
        pnl_today = ctx.formatter.number(paper.get("pnl_today"), 4)
        pnl_total = ctx.formatter.number(paper.get("pnl_total"), 4)
        active_symbols = ctx.formatter.number(paper.get("active_symbols"), 0)

        kg_nodes = ctx.formatter.number(kg.get("nodes"), 0)
        kg_edges = ctx.formatter.number(kg.get("edges"), 0)
        validation_findings = ctx.formatter.number(validation.get("total_findings"), 0)

        next_action = str(data.get("next_action", "PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1"))

        return f"""
        <section class="card">
            <h2>{escape(ctx.formatter.label("ui", "paper_edge_discovery_center"))}</h2>
            <p>Операционный центр Phase II: Paper Runtime → Knowledge Graph → Research → Edge.</p>
            <p>Источник данных: Knowledge Graph API. Прямых SQL-запросов из UI нет.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            {_metric("Paper Runtime", ctx.status.label(paper_status), "Реальные данные paper-контура")}
            {_metric("Closed Trades", closed_total, f"Сегодня: {closed_today}")}
            {_metric("Signals Today", signals_today, f"Fills: {fills_today}")}
            {_metric("P&L Total", pnl_total, f"Сегодня: {pnl_today}")}
        </div>

        <section class="card">
            <h2>Candidate Explainability</h2>
            <p>Назначение: объяснить, почему кандидат попал в TOP и что с ним делать дальше.</p>
            <p>Источник: marketcore_ui.paper_edge_research_candidates_v1 через Knowledge Graph API.</p>
            {_candidate_explainability_table(explanations, ctx)}
        </section>

        <section class="card">
            <h2>TOP Candidates Detail</h2>
            <p>Назначение: быстро понять, какой кандидат готов к следующей проверке, а какой требует накопления выборки.</p>
            {_candidate_detail_table(details, ctx)}
        </section>

        <section class="card">
            <h2>Research Candidates</h2>
            <p>Источник: marketcore_ui.paper_edge_research_candidates_v1</p>
            {_candidate_table(candidates, ctx)}
        </section>

        <section class="card">
            <h2>Paper Runtime Real Data</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Активные инструменты", active_symbols)}
                    {_row("Закрытые сделки всего", closed_total)}
                    {_row("Закрытые сделки сегодня", closed_today)}
                    {_row("Сигналы сегодня", signals_today)}
                    {_row("Исполнения сегодня", fills_today)}
                    {_row("P&L сегодня", pnl_today)}
                    {_row("P&L всего", pnl_total)}
                    {_row("Источник", "marketcore_ui.paper_runtime_summary_v1")}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Knowledge Graph</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Домен", str(kg.get("domain", "PAPER_RUNTIME")))}
                    {_row("Узлы", kg_nodes)}
                    {_row("Связи", kg_edges)}
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Validation</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    {_row("Статус", ctx.status.label(validation_status))}
                    {_row("Findings", validation_findings)}
                </tbody>
            </table>
        </section>


        <section class="card">
            <h2>Sample Collection</h2>
            <p>Сколько Paper-сделок накоплено, сколько ещё нужно до минимальной выборки и какие кандидаты ближе всего к повторной проверке.</p>
            <p><a href="/paper-sample-accumulation-monitor">Открыть Paper Sample Accumulation Monitor</a></p>
            <p>PAPER_RUNTIME_SAMPLE_COLLECTION_DASHBOARD_LINK_V1</p>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>{escape(next_action)}</p>
            <p>PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1</p>
        </section>
        """
