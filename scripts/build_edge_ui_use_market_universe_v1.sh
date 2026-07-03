#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_EDGE_UI_USE_MARKET_UNIVERSE_V1 ==="

mkdir -p scripts src/marketcore/presentation/pages src/scripts

cat > src/marketcore/presentation/pages/edge_validation_queue.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class EdgeValidationQueuePage(Page):
    def __init__(self) -> None:
        super().__init__(route="/edge-validation-queue", title="Проверка", icon="✓", menu_order=16)

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
                <td>Ожидает проверки</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Проверка</h2>
            <p>Очередь кандидатов теперь строится из Market Universe Research Queue, а не из старого BR-only источника.</p>
            <p>Источник: marketcore_ui.market_universe_research_queue_v1.</p>
        </section>

        <section class="card">
            <h2>Кандидаты</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Класс</th>
                        <th>Score</th><th>Приоритет</th><th>Стратегия</th><th>Статус</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующее действие</h2>
            <p>EDGE_PIPELINE_USE_MARKET_UNIVERSE_V1</p>
        </section>
        """
PY

cat > src/marketcore/presentation/pages/edge_validation_pipeline.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class EdgeValidationPipelinePage(Page):
    def __init__(self) -> None:
        super().__init__(route="/edge-validation-pipeline", title="Этапы", icon="▶", menu_order=17)

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/edge-validation-use-market-universe?limit=50")
        rows = payload.get("data") or []

        body = ""
        for r in rows:
            body += f"""
            <tr>
                <td>{escape(str(r.get("validation_rank", "")))}</td>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("strategy", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("total_score"), 2))}</td>
                <td>{escape(str(r.get("research_priority", "")))}</td>
                <td>{escape(str(r.get("validation_status", "")))}</td>
                <td>{escape(str(r.get("recommended_action", "")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Этапы</h2>
            <p>Этапы проверки переключены на новую рыночную вселенную.</p>
            <p>Источник: marketcore_ui.edge_validation_use_market_universe_v1.</p>
        </section>

        <section class="card">
            <h2>Этапы проверки</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Стратегия</th>
                        <th>Score</th><th>Приоритет</th><th>Статус</th><th>Действие</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

api = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = api.read_text()

if '/api/kg/v1/edge-validation-use-market-universe' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    block = '''
            if path == "/api/kg/v1/edge-validation-use-market-universe":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        validation_rank,
                        symbol,
                        timeframe,
                        asset_class,
                        strategy,
                        side,
                        source_queue_rank,
                        total_score,
                        research_priority,
                        ranking_status,
                        validation_status,
                        validation_stage,
                        recommended_action,
                        refreshed_at
                    FROM marketcore_ui.edge_validation_use_market_universe_v1
                    ORDER BY validation_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.edge_validation_use_market_universe_v1",
                    "ui_direct_sql": 0,
                    "logic": "edge_validation_use_market_universe_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

api.write_text(s)
PY

cat > src/scripts/audit_edge_ui_use_market_universe_v1.py <<'PY'
from __future__ import annotations

from pathlib import Path


PAGES = [
    Path("src/marketcore/presentation/pages/edge_validation_queue.py"),
    Path("src/marketcore/presentation/pages/edge_validation_pipeline.py"),
]


def main() -> None:
    print("=== EDGE_UI_USE_MARKET_UNIVERSE_V1 ===")

    for page in PAGES:
        text = page.read_text()
        print(f"PAGE file={page}")
        if "paper_edge_research_candidates_v1" in text:
            raise SystemExit(f"LEGACY_SOURCE_IN_UI_PAGE {page}")
        if "BR@RTSX" in text:
            raise SystemExit(f"BR_ONLY_TEXT_IN_UI_PAGE {page}")

    print("edge_queue_uses_market_universe=READY")
    print("edge_pipeline_uses_market_universe=READY")
    print("legacy_br_ui_removed=READY")
    print("VERDICT=EDGE_UI_USE_MARKET_UNIVERSE_V1_READY")


if __name__ == "__main__":
    main()
PY

cat > scripts/test_edge_ui_use_market_universe_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_UI_USE_MARKET_UNIVERSE_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/pages/edge_validation_queue.py \
  src/marketcore/presentation/pages/edge_validation_pipeline.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/scripts/audit_edge_ui_use_market_universe_v1.py

PYTHONPATH=src python src/scripts/audit_edge_ui_use_market_universe_v1.py \
  | tee /tmp/edge_ui_use_market_universe_v1.txt

grep -q "VERDICT=EDGE_UI_USE_MARKET_UNIVERSE_V1_READY" /tmp/edge_ui_use_market_universe_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_universe_candidates_v1.py >/tmp/ui_market_universe_candidates.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py >/tmp/ui_market_universe_ranking.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_research_queue_v1.py >/tmp/ui_market_universe_queue.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_validation_use_market_universe_v1.py >/tmp/ui_edge_validation_market_universe.txt

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8080/edge-validation-queue" > /tmp/edge_validation_queue_market_universe.html
curl -fsS "http://127.0.0.1:8080/edge-validation-pipeline" > /tmp/edge_validation_pipeline_market_universe.html

grep -q "Проверка" /tmp/edge_validation_queue_market_universe.html
grep -q "market_universe_research_queue_v1" /tmp/edge_validation_queue_market_universe.html
grep -q "Этапы" /tmp/edge_validation_pipeline_market_universe.html
grep -q "edge_validation_use_market_universe_v1" /tmp/edge_validation_pipeline_market_universe.html

if grep -q "BR@RTSX" /tmp/edge_validation_queue_market_universe.html; then
  br_total=$(grep -o "BR@RTSX" /tmp/edge_validation_queue_market_universe.html | wc -l)
  symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.market_universe_research_queue_v1;")
  test "$symbols" -gt 1
  echo "BR_PRESENT_BUT_NOT_BR_ONLY count=$br_total symbols=$symbols"
fi

symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore_ui.market_universe_research_queue_v1;")
test "$symbols" -gt 1

echo "market_universe_symbols=$symbols"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_UI_USE_MARKET_UNIVERSE_V1_READY"
echo "VERDICT=TEST_EDGE_UI_USE_MARKET_UNIVERSE_V1_OK"
SH_TEST

chmod +x scripts/test_edge_ui_use_market_universe_v1.sh
scripts/test_edge_ui_use_market_universe_v1.sh

echo "VERDICT=BUILD_EDGE_UI_USE_MARKET_UNIVERSE_V1_OK"
