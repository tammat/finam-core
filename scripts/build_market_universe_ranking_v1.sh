#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MARKET_UNIVERSE_RANKING_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/033_market_universe_ranking_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.market_universe_ranking_v1 (
    rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    data_age_sec INTEGER,

    freshness_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    history_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    liquidity_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    timeframe_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    asset_priority_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    total_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    ranking_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_version TEXT NOT NULL DEFAULT 'MARKET_UNIVERSE_RANKING_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual',

    UNIQUE(symbol, timeframe)
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.market_universe_ranking_v1 TO alex;

COMMIT;

SELECT 'MARKET_UNIVERSE_RANKING_SCHEMA_V1_READY' AS verdict;
SQL

cat > src/scripts/build_market_universe_ranking_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_UNIVERSE_RANKING_V1"


def clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def timeframe_score(tf: str) -> float:
    return {"M5": 1.0, "M1": 0.85, "H1": 0.70, "M15": 0.65}.get(tf, 0.4)


def asset_priority(asset: str) -> float:
    return {
        "FUTURES": 1.0,
        "EQUITY_OR_FX_SPOT": 0.95,
        "CRYPTO_PROXY": 0.75,
        "INDEX": 0.60,
    }.get(asset, 0.40)


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== MARKET_UNIVERSE_RANKING_V1 ===")

            cur.execute("""
                SELECT *
                FROM marketcore_ui.paper_edge_market_universe_candidates_v1
                ORDER BY candidate_rank;
            """)
            rows = [dict(r) for r in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.market_universe_ranking_v1;")

            ranked = []
            max_volume = max([float(r.get("latest_volume") or 0) for r in rows] or [1.0])

            for r in rows:
                age = int(r.get("data_age_sec") or 999999999)
                bars = int(r.get("bars_total") or 0)
                volume = float(r.get("latest_volume") or 0)
                tf = str(r.get("timeframe") or "")
                asset = str(r.get("asset_class") or "UNKNOWN")

                freshness = clamp(1.0 - age / 172800.0)
                history = clamp(bars / 10000.0)
                liquidity = clamp(volume / max_volume) if max_volume > 0 else 0.0
                tf_score = timeframe_score(tf)
                asset_score = asset_priority(asset)

                total = (
                    freshness * 35.0 +
                    history * 25.0 +
                    liquidity * 15.0 +
                    tf_score * 15.0 +
                    asset_score * 10.0
                )

                if total >= 80:
                    status = "READY_FOR_RESEARCH"
                    action = "Добавить в TOP research queue."
                elif freshness < 0.2:
                    status = "WAIT_FRESH_DATA"
                    action = "Ждать обновления market bars."
                else:
                    status = "WATCHLIST"
                    action = "Оставить в наблюдении."

                ranked.append((total, r, freshness, history, liquidity, tf_score, asset_score, status, action))

            ranked.sort(key=lambda x: x[0], reverse=True)

            for rank, item in enumerate(ranked, start=1):
                total, r, freshness, history, liquidity, tf_score, asset_score, status, action = item

                cur.execute("""
                    INSERT INTO marketcore_ui.market_universe_ranking_v1 (
                        rank, symbol, timeframe, asset_class,
                        bars_total, latest_ts, latest_close, latest_volume, data_age_sec,
                        freshness_score, history_score, liquidity_score, timeframe_score,
                        asset_priority_score, total_score,
                        ranking_status, recommended_action,
                        source_version, refreshed_at, build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    rank, r["symbol"], r["timeframe"], r["asset_class"],
                    r["bars_total"], r["latest_ts"], r["latest_close"], r["latest_volume"], r["data_age_sec"],
                    freshness * 100, history * 100, liquidity * 100, tf_score * 100,
                    asset_score * 100, total,
                    status, action,
                    SOURCE_VERSION, build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.market_universe_ranking_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT ranking_status, count(*) AS rows
                FROM marketcore_ui.market_universe_ranking_v1
                GROUP BY ranking_status
                ORDER BY ranking_status;
            """)
            groups = cur.fetchall()

    print(f"rows_written={rows_written}")
    for g in groups:
        print(f"ranking_status_{g['ranking_status']}={g['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_UNIVERSE_RANKING_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/market-universe-ranking' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    block = '''
            if path == "/api/kg/v1/market-universe-ranking":
                limit = int(q.get("limit", ["100"])[0])
                rows = fetch_all("""
                    SELECT
                        rank, symbol, timeframe, asset_class,
                        bars_total, latest_ts, latest_close, latest_volume, data_age_sec,
                        freshness_score, history_score, liquidity_score, timeframe_score,
                        asset_priority_score, total_score,
                        ranking_status, recommended_action, refreshed_at
                    FROM marketcore_ui.market_universe_ranking_v1
                    ORDER BY rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.market_universe_ranking_v1",
                    "ui_direct_sql": 0,
                    "logic": "market_universe_ranking_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/market_universe_ranking.py <<'PY'
from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


class MarketUniverseRankingPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/market-universe-ranking",
            title="Рейтинг рыночной вселенной",
            icon="★",
            menu_order=24,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/market-universe-ranking?limit=100")
        rows = payload.get("data") or []

        body = ""
        for r in rows:
            body += f"""
            <tr>
                <td>{escape(str(r.get("rank", "")))}</td>
                <td>{escape(str(r.get("symbol", "")))}</td>
                <td>{escape(str(r.get("timeframe", "")))}</td>
                <td>{escape(str(r.get("asset_class", "")))}</td>
                <td>{escape(ctx.formatter.number(r.get("total_score"), 2))}</td>
                <td>{escape(ctx.formatter.number(r.get("freshness_score"), 1))}</td>
                <td>{escape(ctx.formatter.number(r.get("history_score"), 1))}</td>
                <td>{escape(ctx.formatter.number(r.get("liquidity_score"), 1))}</td>
                <td>{escape(str(r.get("ranking_status", "")))}</td>
                <td>{escape(str(r.get("recommended_action", "")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>Рейтинг рыночной вселенной</h2>
            <p>Единый рейтинг инструментов для Research / Edge Discovery.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.market_universe_ranking_v1.</p>
        </section>

        <section class="card">
            <h2>TOP Universe</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th><th>Инструмент</th><th>TF</th><th>Asset</th>
                        <th>Total</th><th>Fresh</th><th>History</th><th>Liquidity</th>
                        <th>Status</th><th>Действие</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>Следующее действие</h2>
            <p>MARKET_UNIVERSE_RESEARCH_QUEUE_V1</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/ui_labels.py")
s = p.read_text()
if '"/market-universe-ranking"' not in s:
    s = s.replace(
        '    "/paper-edge-market-symbol-alias-plan": "План alias рыночных символов",\n',
        '    "/paper-edge-market-symbol-alias-plan": "План alias рыночных символов",\n'
        '    "/market-universe-ranking": "Рейтинг рыночной вселенной",\n',
    )
p.write_text(s)

p = Path("src/marketcore/presentation/route_groups.py")
s = p.read_text()
if '"/market-universe-ranking"' not in s:
    s = s.replace(
        '            "/paper-edge-market-symbol-alias-plan",\n',
        '            "/paper-edge-market-symbol-alias-plan",\n'
        '            "/market-universe-ranking",\n',
    )
p.write_text(s)

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()
if "MarketUniverseRankingPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.market_universe_ranking import MarketUniverseRankingPage\n",
    )
if "MarketUniverseRankingPage()," not in s:
    s = s.replace(
        "PaperEdgeMarketSymbolAliasPlanPage(),",
        "PaperEdgeMarketSymbolAliasPlanPage(),\n    MarketUniverseRankingPage(),",
    )
p.write_text(s)
PY

cat > scripts/test_market_universe_ranking_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_UNIVERSE_RANKING_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/033_market_universe_ranking_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_universe_ranking_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/market_universe_ranking.py \
  src/marketcore/presentation/registry.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_universe_ranking_v1.py \
  | tee /tmp/market_universe_ranking_v1.txt

grep -q "VERDICT=MARKET_UNIVERSE_RANKING_V1_READY" /tmp/market_universe_ranking_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_ranking_v1;")
ready=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.market_universe_ranking_v1 WHERE ranking_status='READY_FOR_RESEARCH';")

test "$rows" -gt 0
test "$ready" -gt 0

sudo systemctl restart marketcore-kg-api.service
sudo systemctl restart marketcore-ui-shell.service
sleep 2

curl -fsS "http://127.0.0.1:8095/api/kg/v1/market-universe-ranking?limit=10" > /tmp/market_universe_ranking_api.json
curl -fsS "http://127.0.0.1:8080/market-universe-ranking" > /tmp/market_universe_ranking_page.html

grep -q '"status": "OK"' /tmp/market_universe_ranking_api.json
grep -q '"total_score"' /tmp/market_universe_ranking_api.json
grep -q "Рейтинг рыночной вселенной" /tmp/market_universe_ranking_page.html
grep -q "MARKET_UNIVERSE_RESEARCH_QUEUE_V1" /tmp/market_universe_ranking_page.html

psql -d finam_core -c "
SELECT rank, symbol, timeframe, asset_class, total_score, ranking_status
FROM marketcore_ui.market_universe_ranking_v1
ORDER BY rank
LIMIT 20;
"

echo "ranking_rows=$rows"
echo "ready_for_research=$ready"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKET_UNIVERSE_RANKING_V1_OK"
SH_TEST

chmod +x scripts/test_market_universe_ranking_v1.sh

scripts/test_market_universe_ranking_v1.sh

echo "VERDICT=BUILD_MARKET_UNIVERSE_RANKING_V1_OK"
