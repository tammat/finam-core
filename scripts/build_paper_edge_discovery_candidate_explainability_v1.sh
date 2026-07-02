#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1 ==="

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-edge-candidate-explainability' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-edge-candidate-explainability":
                limit = int(q.get("limit", ["10"])[0])
                rows = fetch_all("""
                    SELECT
                        candidate_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        candidate_status,
                        expectancy,
                        profit_factor,
                        winrate,
                        trades,
                        net_pnl,
                        score,
                        source_table,
                        refreshed_at,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN 'LOW_SAMPLE'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN 'REVIEW_READY'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN 'OBSERVE'
                            ELSE 'REJECT_REVIEW'
                        END AS explainability_status,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN
                                'Кандидат найден, но выборка недостаточна для вывода об устойчивом преимуществе.'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN
                                'Кандидат имеет положительное матожидание и Profit Factor выше минимального порога.'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN
                                'Кандидат не показывает явного отрицательного результата, но требует дополнительного наблюдения.'
                            ELSE
                                'Текущая статистика не подтверждает преимущество для продвижения.'
                        END AS why_selected,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN
                                'Главный риск: малая выборка. Требуется накопить больше Paper-сделок.'
                            WHEN COALESCE(winrate,0) < 0.45 THEN
                                'Главный риск: низкая доля прибыльных сделок, требуется анализ распределения убытков.'
                            WHEN COALESCE(profit_factor,0) < 1.0 THEN
                                'Главный риск: Profit Factor ниже единицы.'
                            ELSE
                                'Ключевые риски: устойчивость по времени, режимам рынка и out-of-sample проверка.'
                        END AS risk_explanation,

                        concat(
                            'Trades=', COALESCE(trades,0),
                            '; PF=', COALESCE(round(profit_factor::numeric,4),0),
                            '; Expectancy=', COALESCE(round(expectancy::numeric,4),0),
                            '; WinRate=', COALESCE(round(winrate::numeric,4),0),
                            '; NetPnL=', COALESCE(round(net_pnl::numeric,4),0)
                        ) AS evidence_summary,

                        CASE
                            WHEN COALESCE(trades,0) < 30 THEN 'ACCUMULATE_SAMPLE'
                            WHEN COALESCE(profit_factor,0) >= 1.2
                             AND COALESCE(expectancy,0) > 0 THEN 'SEND_TO_EDGE_VALIDATION'
                            WHEN COALESCE(profit_factor,0) >= 1.0
                             AND COALESCE(expectancy,0) >= 0 THEN 'OBSERVE_MORE'
                            ELSE 'DO_NOT_PROMOTE'
                        END AS recommended_action

                    FROM marketcore_ui.paper_edge_research_candidates_v1
                    ORDER BY candidate_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_research_candidates_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_candidate_explainability_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_edge_discovery.py <<'PY'
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
            <h2>Next Action</h2>
            <p>{escape(next_action)}</p>
            <p>PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1</p>
        </section>
        """
PY

cat > scripts/test_paper_edge_discovery_candidate_explainability_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_discovery.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/candidate_explainability_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=18395 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_candidate_explainability_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=18380 KG_API_BASE_URL=http://127.0.0.1:18395 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/candidate_explainability_page_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:18395/api/kg/v1/paper-edge-candidate-explainability?limit=5" \
  > /tmp/candidate_explainability_api_v1.json

curl -fsS "http://127.0.0.1:18380/paper-edge-discovery" \
  > /tmp/candidate_explainability_page_v1.html

grep -q '"status": "OK"' /tmp/candidate_explainability_api_v1.json
grep -q '"explainability_status"' /tmp/candidate_explainability_api_v1.json
grep -q '"why_selected"' /tmp/candidate_explainability_api_v1.json
grep -q '"risk_explanation"' /tmp/candidate_explainability_api_v1.json
grep -q '"recommended_action"' /tmp/candidate_explainability_api_v1.json

grep -q "Candidate Explainability" /tmp/candidate_explainability_page_v1.html
grep -q "Почему выбран" /tmp/candidate_explainability_page_v1.html
grep -q "Доказательства" /tmp/candidate_explainability_page_v1.html
grep -q "Риски" /tmp/candidate_explainability_page_v1.html
grep -q "Рекомендация" /tmp/candidate_explainability_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1" /tmp/candidate_explainability_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/candidate_explainability_page_v1.html

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_candidate_explainability_v1.sh

scripts/test_paper_edge_discovery_candidate_explainability_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_CANDIDATE_EXPLAINABILITY_V1_OK"
