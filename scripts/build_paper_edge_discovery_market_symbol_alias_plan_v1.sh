#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/030_paper_edge_market_symbol_alias_plan_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_symbol_alias_plan_v1 (
    plan_rank INTEGER PRIMARY KEY,

    candidate_symbol TEXT NOT NULL DEFAULT '',
    candidate_root TEXT NOT NULL DEFAULT '',
    candidate_strategy TEXT NOT NULL DEFAULT '',
    candidate_timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    alias_symbol TEXT NOT NULL DEFAULT '',
    alias_timeframe TEXT NOT NULL DEFAULT '',
    alias_source_table TEXT NOT NULL DEFAULT '',

    alias_bars_total INTEGER NOT NULL DEFAULT 0,
    alias_latest_bar_ts TIMESTAMPTZ,
    alias_market_data_age_sec INTEGER,

    alias_match_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    alias_confidence NUMERIC(10,4) NOT NULL DEFAULT 0,

    alias_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_freshness_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_symbol_alias_plan_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_SYMBOL_ALIAS_PLAN_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_edge_market_symbol_alias_plan_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/030_paper_edge_market_symbol_alias_plan_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_edge_market_symbol_alias_plan_v1.sh

cat > src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py <<'PY'
from __future__ import annotations

import os
import re
import uuid
from decimal import Decimal

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1"

MONTH_CODES = set("FGHJKMNQUVXZ")


def clean_symbol(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (value or "").upper())


def candidate_root(symbol: str) -> str:
    raw = (symbol or "").upper()
    base = raw.split("@", 1)[0]
    base = base.replace("_ROLLING", "").replace("_CONT", "").replace("CONT", "")

    # BRN6 -> BR, NGM6 -> NG, GDU6 -> GD
    if len(base) >= 4 and base[-2:].isalnum() and base[-2:-1] in MONTH_CODES and base[-1:].isdigit():
        return base[:-2]

    # USDRUBF -> USDRUB, SiH6 -> SI etc.
    if len(base) >= 4 and base[-1:] in MONTH_CODES:
        return base[:-1]

    return re.sub(r"[^A-Z0-9]", "", base)


def score_alias(candidate_symbol: str, market_symbol: str) -> tuple[str, Decimal]:
    c_clean = clean_symbol(candidate_symbol)
    m_clean = clean_symbol(market_symbol)
    root = candidate_root(candidate_symbol)

    if not c_clean or not m_clean:
        return "NO_MATCH", Decimal("0.0000")

    if c_clean == m_clean:
        return "EXACT_CLEAN_MATCH", Decimal("1.0000")

    if candidate_symbol.upper() == market_symbol.upper():
        return "EXACT_SYMBOL_MATCH", Decimal("1.0000")

    if root and m_clean == root:
        return "ROOT_EXACT_MATCH", Decimal("0.9500")

    if root and (m_clean.startswith(root) or root.startswith(m_clean)):
        return "ROOT_PREFIX_MATCH", Decimal("0.8500")

    if root and root in m_clean:
        return "ROOT_CONTAINS_MATCH", Decimal("0.7500")

    c_prefix = c_clean[:3]
    m_prefix = m_clean[:3]
    if c_prefix and c_prefix == m_prefix:
        return "PREFIX3_MATCH", Decimal("0.6500")

    c_prefix2 = c_clean[:2]
    m_prefix2 = m_clean[:2]
    if c_prefix2 and c_prefix2 == m_prefix2:
        return "PREFIX2_MATCH", Decimal("0.5000")

    return "NO_MATCH", Decimal("0.0000")


def classify(match_type: str, confidence: Decimal, age_sec) -> tuple[str, str, str]:
    if match_type == "NO_MATCH":
        return (
            "NO_ALIAS_FOUND",
            "Не найден подходящий market symbol.",
            "Добавить ручной alias или проверить backfill market_bars.",
        )

    if age_sec is None:
        return (
            "ALIAS_FOUND_UNKNOWN_FRESHNESS",
            "Похожий market symbol найден, но свежесть не определена.",
            "Проверить timestamp market_bars.",
        )

    if confidence >= Decimal("0.85"):
        return (
            "ALIAS_CANDIDATE_STRONG",
            "Найден сильный кандидат на alias для market data binding.",
            "Добавить alias в следующий слой alias-словаря и повторить binding.",
        )

    if confidence >= Decimal("0.50"):
        return (
            "ALIAS_CANDIDATE_WEAK",
            "Найден слабый кандидат на alias, требуется ручная проверка.",
            "Проверить соответствие инструмента вручную до применения.",
        )

    return (
        "NO_ALIAS_FOUND",
        "Совпадение недостаточно сильное.",
        "Не применять автоматически.",
    )


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1 ===")

            cur.execute("""
                SELECT
                    freshness_rank,
                    candidate_symbol,
                    candidate_strategy,
                    candidate_timeframe,
                    side
                FROM marketcore_ui.paper_edge_market_data_freshness_v1
                WHERE row_type='CANDIDATE_BINDING'
                ORDER BY freshness_rank;
            """)
            candidates = [dict(row) for row in cur.fetchall()]

            cur.execute("""
                SELECT
                    freshness_rank,
                    market_symbol,
                    market_timeframe,
                    source_table,
                    bars_total,
                    latest_bar_ts,
                    market_data_age_sec
                FROM marketcore_ui.paper_edge_market_data_freshness_v1
                WHERE row_type='SOURCE_LATEST'
                ORDER BY market_symbol, market_timeframe;
            """)
            market_rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")

            plan_rows: list[dict] = []

            for candidate in candidates:
                symbol = str(candidate.get("candidate_symbol") or "")
                root = candidate_root(symbol)

                scored: list[dict] = []

                for market in market_rows:
                    market_symbol = str(market.get("market_symbol") or "")
                    match_type, confidence = score_alias(symbol, market_symbol)

                    if confidence <= Decimal("0"):
                        continue

                    alias_status, diagnosis, action = classify(
                        match_type=match_type,
                        confidence=confidence,
                        age_sec=market.get("market_data_age_sec"),
                    )

                    scored.append(
                        {
                            "candidate_symbol": symbol,
                            "candidate_root": root,
                            "candidate_strategy": candidate.get("candidate_strategy") or "",
                            "candidate_timeframe": candidate.get("candidate_timeframe") or "",
                            "side": candidate.get("side") or "",
                            "alias_symbol": market_symbol,
                            "alias_timeframe": market.get("market_timeframe") or "",
                            "alias_source_table": market.get("source_table") or "",
                            "alias_bars_total": int(market.get("bars_total") or 0),
                            "alias_latest_bar_ts": market.get("latest_bar_ts"),
                            "alias_market_data_age_sec": market.get("market_data_age_sec"),
                            "alias_match_type": match_type,
                            "alias_confidence": confidence,
                            "alias_status": alias_status,
                            "diagnosis": diagnosis,
                            "recommended_action": action,
                            "source_freshness_rank": market.get("freshness_rank"),
                        }
                    )

                scored.sort(
                    key=lambda row: (
                        row["alias_confidence"],
                        row["alias_bars_total"],
                        -(row["alias_market_data_age_sec"] or 999999999),
                    ),
                    reverse=True,
                )

                if scored:
                    plan_rows.extend(scored[:3])
                else:
                    plan_rows.append(
                        {
                            "candidate_symbol": symbol,
                            "candidate_root": root,
                            "candidate_strategy": candidate.get("candidate_strategy") or "",
                            "candidate_timeframe": candidate.get("candidate_timeframe") or "",
                            "side": candidate.get("side") or "",
                            "alias_symbol": "",
                            "alias_timeframe": "",
                            "alias_source_table": "",
                            "alias_bars_total": 0,
                            "alias_latest_bar_ts": None,
                            "alias_market_data_age_sec": None,
                            "alias_match_type": "NO_MATCH",
                            "alias_confidence": Decimal("0.0000"),
                            "alias_status": "NO_ALIAS_FOUND",
                            "diagnosis": "По кандидату не найден похожий market symbol среди свежих market bars.",
                            "recommended_action": "Добавить ручной alias или проверить backfill market_bars.",
                            "source_freshness_rank": candidate.get("freshness_rank"),
                        }
                    )

            for idx, row in enumerate(plan_rows, start=1):
                cur.execute("""
                    INSERT INTO marketcore_ui.paper_edge_market_symbol_alias_plan_v1 (
                        plan_rank,
                        candidate_symbol,
                        candidate_root,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        alias_symbol,
                        alias_timeframe,
                        alias_source_table,
                        alias_bars_total,
                        alias_latest_bar_ts,
                        alias_market_data_age_sec,
                        alias_match_type,
                        alias_confidence,
                        alias_status,
                        diagnosis,
                        recommended_action,
                        source_freshness_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    idx,
                    row["candidate_symbol"],
                    row["candidate_root"],
                    row["candidate_strategy"],
                    row["candidate_timeframe"],
                    row["side"],
                    row["alias_symbol"],
                    row["alias_timeframe"],
                    row["alias_source_table"],
                    row["alias_bars_total"],
                    row["alias_latest_bar_ts"],
                    row["alias_market_data_age_sec"],
                    row["alias_match_type"],
                    row["alias_confidence"],
                    row["alias_status"],
                    row["diagnosis"],
                    row["recommended_action"],
                    row["source_freshness_rank"],
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT alias_status, count(*) AS rows
                FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
                GROUP BY alias_status
                ORDER BY alias_status;
            """)
            status_rows = cur.fetchall()

    print(f"candidates={len(candidates)}")
    print(f"market_rows={len(market_rows)}")
    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"alias_status_{row['alias_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-edge-market-symbol-alias-plan' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-edge-market-symbol-alias-plan":
                limit = int(q.get("limit", ["100"])[0])
                rows = fetch_all("""
                    SELECT
                        plan_rank,
                        candidate_symbol,
                        candidate_root,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        alias_symbol,
                        alias_timeframe,
                        alias_source_table,
                        alias_bars_total,
                        alias_latest_bar_ts,
                        alias_market_data_age_sec,
                        alias_match_type,
                        alias_confidence,
                        alias_status,
                        diagnosis,
                        recommended_action,
                        source_freshness_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
                    ORDER BY plan_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_market_symbol_alias_plan_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_discovery_market_symbol_alias_plan_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_edge_market_symbol_alias_plan.py <<'PY'
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
        return "<p>План alias пуст.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("plan_rank", "")))}</td>
            <td>{escape(str(row.get("candidate_symbol", "")))}</td>
            <td>{escape(str(row.get("candidate_root", "")))}</td>
            <td>{escape(str(row.get("candidate_strategy", "")))}</td>
            <td>{escape(str(row.get("candidate_timeframe", "")))}</td>
            <td>{escape(str(row.get("alias_symbol", "")))}</td>
            <td>{escape(str(row.get("alias_timeframe", "")))}</td>
            <td>{escape(str(row.get("alias_source_table", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("alias_bars_total"), 0))}</td>
            <td>{escape(ctx.formatter.datetime(row.get("alias_latest_bar_ts")))}</td>
            <td>{escape(ctx.formatter.number(row.get("alias_market_data_age_sec"), 0))}</td>
            <td>{escape(str(row.get("alias_match_type", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("alias_confidence"), 4))}</td>
            <td>{escape(str(row.get("alias_status", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Кандидат</th>
                <th>Root</th>
                <th>Стратегия</th>
                <th>TF</th>
                <th>Alias Symbol</th>
                <th>Alias TF</th>
                <th>Источник</th>
                <th>Баров</th>
                <th>Последний бар</th>
                <th>Age sec</th>
                <th>Match</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeMarketSymbolAliasPlanPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-market-symbol-alias-plan",
            title="План alias рыночных символов",
            icon="◎",
            menu_order=23,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-edge-market-symbol-alias-plan?limit=100")
        rows = payload.get("data") or []

        strong = sum(1 for row in rows if row.get("alias_status") == "ALIAS_CANDIDATE_STRONG")
        weak = sum(1 for row in rows if row.get("alias_status") == "ALIAS_CANDIDATE_WEAK")
        missing = sum(1 for row in rows if row.get("alias_status") == "NO_ALIAS_FOUND")

        return f"""
        <section class="card">
            <h2>План alias рыночных символов</h2>
            <p>План предлагает соответствия между Paper-кандидатами и символами из market_bars.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_edge_market_symbol_alias_plan_v1.</p>
            <p><a href="/paper-edge-market-data-freshness">← Свежесть рыночных данных</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            {_metric("Всего строк", ctx.formatter.number(len(rows), 0))}
            {_metric("Strong Alias", ctx.formatter.number(strong, 0))}
            {_metric("Weak Alias", ctx.formatter.number(weak, 0))}
            {_metric("No Alias", ctx.formatter.number(missing, 0))}
        </div>

        <section class="card">
            <h2>Alias Plan</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Вывод</h2>
            <p>Сильные alias можно вынести в постоянный словарь соответствий. Слабые alias требуют ручной проверки.</p>
            <p>Следующий шаг: PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_APPLY_V1.</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/pages/paper_edge_market_data_freshness.py")
s = p.read_text()

if "/paper-edge-market-symbol-alias-plan" not in s:
    block = '''
        <section class="card">
            <h2>Alias Plan</h2>
            <p><a href="/paper-edge-market-symbol-alias-plan">Открыть план alias рыночных символов</a></p>
            <p>PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1</p>
        </section>
'''
    needle = '        <section class="card">\n            <h2>Вывод</h2>'
    if needle in s:
        s = s.replace(needle, block + "\n" + needle)
    else:
        s = s.replace('        """', block + '\n        """')

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/ui_labels.py")
s = p.read_text()

if '"/paper-edge-market-symbol-alias-plan"' not in s:
    s = s.replace(
        '    "/paper-edge-market-data-freshness": "Свежесть рыночных данных",\n',
        '    "/paper-edge-market-data-freshness": "Свежесть рыночных данных",\n'
        '    "/paper-edge-market-symbol-alias-plan": "План alias рыночных символов",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/route_groups.py")
s = p.read_text()

if '"/paper-edge-market-symbol-alias-plan"' not in s:
    s = s.replace(
        '            "/paper-edge-market-data-freshness",\n',
        '            "/paper-edge-market-data-freshness",\n'
        '            "/paper-edge-market-symbol-alias-plan",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperEdgeMarketSymbolAliasPlanPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_edge_market_symbol_alias_plan import PaperEdgeMarketSymbolAliasPlanPage\n",
    )

if "PaperEdgeMarketSymbolAliasPlanPage()," not in s:
    if "PaperEdgeMarketDataFreshnessPage()," in s:
        s = s.replace(
            "PaperEdgeMarketDataFreshnessPage(),",
            "PaperEdgeMarketDataFreshnessPage(),\n    PaperEdgeMarketSymbolAliasPlanPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperEdgeMarketSymbolAliasPlanPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_edge_discovery_market_symbol_alias_plan_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1 ==="

scripts/apply_paper_edge_market_symbol_alias_plan_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_market_symbol_alias_plan.py \
  src/marketcore/presentation/pages/paper_edge_market_data_freshness.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_market_symbol_alias_plan.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_binding_v1.py \
  > /tmp/alias_plan_binding_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_freshness_v1.py \
  > /tmp/alias_plan_freshness_builder_v1.txt

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_paper_edge_market_symbol_alias_plan_v1.py \
  | tee /tmp/paper_edge_market_symbol_alias_plan_builder_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY" \
  /tmp/paper_edge_market_symbol_alias_plan_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20795 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_alias_plan_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20780 KG_API_BASE_URL=http://127.0.0.1:20795 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/alias_plan_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20795/api/kg/v1/paper-edge-market-symbol-alias-plan?limit=100" \
  > /tmp/paper_edge_market_symbol_alias_plan_api_v1.json

curl -fsS "http://127.0.0.1:20780/paper-edge-market-symbol-alias-plan" \
  > /tmp/paper_edge_market_symbol_alias_plan_page_v1.html

curl -fsS "http://127.0.0.1:20780/paper-edge-market-data-freshness" \
  > /tmp/paper_edge_market_data_freshness_alias_link_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"candidate_symbol"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"alias_symbol"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"alias_status"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json
grep -q '"alias_confidence"' /tmp/paper_edge_market_symbol_alias_plan_api_v1.json

grep -q "План alias рыночных символов" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html
grep -q "Alias Plan" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_APPLY_V1" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_market_symbol_alias_plan_page_v1.html

grep -q "paper-edge-market-symbol-alias-plan" /tmp/paper_edge_market_data_freshness_alias_link_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1" /tmp/paper_edge_market_data_freshness_alias_link_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")
candidates=$(psql -At -d finam_core -c "SELECT count(DISTINCT candidate_symbol) FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1;")

test "$rows" -gt 0
test "$candidates" -gt 0

psql -d finam_core -c "
SELECT
    alias_status,
    alias_match_type,
    count(*) AS rows
FROM marketcore_ui.paper_edge_market_symbol_alias_plan_v1
GROUP BY alias_status, alias_match_type
ORDER BY alias_status, alias_match_type;
"

echo "alias_plan_rows=$rows"
echo "alias_plan_candidates=$candidates"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_market_symbol_alias_plan_v1.sh

scripts/test_paper_edge_discovery_market_symbol_alias_plan_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1_OK"
