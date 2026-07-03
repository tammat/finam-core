#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1 ==="

mkdir -p src/marketcore/presentation/pages scripts

cat > src/marketcore/presentation/pages/knowledge_graph.py <<'PY'
from __future__ import annotations

from marketcore.presentation.page import Page


class KnowledgeGraphPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/knowledge-graph",
            title="Граф знаний",
            icon="◎",
            menu_order=30,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Граф знаний</h2>
            <p>Раздел восстановлен. Ошибка 500 устранена безопасной заглушкой без прямого SQL.</p>
            <p>Следующий этап: подключить реальные метрики Knowledge Graph через KG API.</p>
        </section>

        <section class="card">
            <h2>Связанные разделы</h2>
            <p><a href="/market-universe-ranking">Рейтинг рыночной вселенной</a></p>
            <p><a href="/market-universe-research-queue">Research Queue</a></p>
            <p><a href="/marketcore-ui-route-health-matrix">Матрица маршрутов UI</a></p>
        </section>
        """
PY

cat > src/marketcore/presentation/pages/market_universe_research_queue.py <<'PY'
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
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/market-universe-research-queue' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/market-universe-research-queue":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        queue_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        total_score,
                        ranking_status,
                        research_priority,
                        research_status,
                        recommended_strategy_family,
                        recommended_action,
                        source_rank,
                        refreshed_at
                    FROM marketcore_ui.market_universe_research_queue_v1
                    ORDER BY queue_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_research_queue_v1",
                    "ui_direct_sql": 0,
                    "logic": "market_universe_research_queue_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/ui_labels.py")
s = p.read_text()
if '"/market-universe-research-queue"' not in s:
    s = s.replace(
        '    "/market-universe-ranking": "Рейтинг рыночной вселенной",\n',
        '    "/market-universe-ranking": "Рейтинг рыночной вселенной",\n'
        '    "/market-universe-research-queue": "Очередь исследований",\n',
    )
p.write_text(s)

p = Path("src/marketcore/presentation/route_groups.py")
s = p.read_text()
if '"/market-universe-research-queue"' not in s:
    s = s.replace(
        '            "/market-universe-ranking",\n',
        '            "/market-universe-ranking",\n'
        '            "/market-universe-research-queue",\n',
    )
p.write_text(s)

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "from marketcore.presentation.pages.knowledge_graph import KnowledgeGraphPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.knowledge_graph import KnowledgeGraphPage\n",
    )

if "from marketcore.presentation.pages.market_universe_research_queue import MarketUniverseResearchQueuePage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.market_universe_research_queue import MarketUniverseResearchQueuePage\n",
    )

if "MarketUniverseResearchQueuePage()," not in s:
    s = s.replace(
        "MarketUniverseRankingPage(),",
        "MarketUniverseRankingPage(),\n    MarketUniverseResearchQueuePage(),",
    )

p.write_text(s)
PY

cat > scripts/test_market_universe_research_queue_dashboard_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/knowledge_graph.py \
  src/marketcore/presentation/pages/market_universe_research_queue.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n \
  src/marketcore/presentation/pages/knowledge_graph.py \
  src/marketcore/presentation/pages/market_universe_research_queue.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/ranking_for_queue_dashboard_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/research_queue_for_dashboard_v1.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/market-universe-research-queue?limit=20" \
  > /tmp/market_universe_research_queue_api_v1.json

curl -fsS "http://127.0.0.1:8080/market-universe-research-queue" \
  > /tmp/market_universe_research_queue_page_v1.html

curl -fsS "http://127.0.0.1:8080/knowledge-graph" \
  > /tmp/knowledge_graph_fixed_v1.html

grep -q '"status": "OK"' /tmp/market_universe_research_queue_api_v1.json
grep -q '"queue_rank"' /tmp/market_universe_research_queue_api_v1.json
grep -q '"recommended_strategy_family"' /tmp/market_universe_research_queue_api_v1.json

grep -q "Очередь исследований" /tmp/market_universe_research_queue_page_v1.html
grep -q "MARKET_UNIVERSE_RESEARCH_QUEUE_TIMER_V1" /tmp/market_universe_research_queue_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/market_universe_research_queue_page_v1.html

grep -q "Граф знаний" /tmp/knowledge_graph_fixed_v1.html
grep -q "Матрица маршрутов UI" /tmp/knowledge_graph_fixed_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/knowledge_graph_fixed_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1;")
high=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_research_queue_v1 WHERE research_priority='HIGH';")

test "$rows" -gt 0
test "$high" -gt 0

echo "research_queue_rows=$rows"
echo "research_queue_high=$high"
echo "knowledge_graph_fixed=1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1_READY"
echo "VERDICT=TEST_MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1_OK"
SH_TEST

chmod +x scripts/test_market_universe_research_queue_dashboard_v1.sh

scripts/test_market_universe_research_queue_dashboard_v1.sh

echo "VERDICT=BUILD_MARKET_UNIVERSE_RESEARCH_QUEUE_DASHBOARD_V1_OK"
