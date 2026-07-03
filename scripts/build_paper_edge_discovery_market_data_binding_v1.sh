#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/028_paper_edge_market_data_binding_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_data_binding_v1 (
    binding_rank INTEGER PRIMARY KEY,

    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    market_symbol TEXT NOT NULL DEFAULT '',
    market_timeframe TEXT NOT NULL DEFAULT '',
    bars_source_table TEXT NOT NULL DEFAULT '',

    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_bar_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    market_data_age_sec INTEGER,

    market_data_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    binding_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    binding_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_candidate_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_data_binding_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_DATA_BINDING_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_edge_market_data_binding_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/028_paper_edge_market_data_binding_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_edge_market_data_binding_v1.sh

cat > src/scripts/build_paper_edge_market_data_binding_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from decimal import Decimal

import psycopg2
import psycopg2.extras
from psycopg2 import sql

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1"
FRESH_AFTER_SEC = int(os.getenv("PAPER_EDGE_MARKET_DATA_FRESH_AFTER_SEC", "86400"))

SOURCE_TABLE_CANDIDATES = [
    "public.market_bars",
    "public.market_data_bars",
    "public.bars",
    "public.candles",
    "public.market_candles",
    "public.ohlcv_bars",
]

SYMBOL_COLUMNS = ["symbol", "ticker", "secid", "instrument"]
TIMEFRAME_COLUMNS = ["timeframe", "tf", "interval"]
TS_COLUMNS = ["ts", "bar_ts", "timestamp", "datetime", "time", "created_at"]
CLOSE_COLUMNS = ["close", "c", "last", "price"]
VOLUME_COLUMNS = ["volume", "vol", "v", "qty", "turnover"]


@dataclass(frozen=True)
class MarketSource:
    table: str
    schema: str
    name: str
    symbol_col: str
    timeframe_col: str | None
    ts_col: str
    close_col: str | None
    volume_col: str | None


def table_exists(cur, full_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) AS reg;", (full_name,))
    row = cur.fetchone()
    return bool(row and row["reg"])


def table_columns(cur, full_name: str) -> dict[str, str]:
    schema, name = full_name.split(".", 1)
    cur.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s;
        """,
        (schema, name),
    )
    return {str(r["column_name"]): str(r["data_type"]) for r in cur.fetchall()}


def pick_column(columns: dict[str, str], candidates: list[str], require_time: bool = False) -> str | None:
    lower_map = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lower_map:
            col = lower_map[candidate.lower()]
            if require_time:
                typ = columns[col].lower()
                if "timestamp" not in typ and "date" not in typ:
                    continue
            return col

    return None


def discover_market_source(cur) -> MarketSource | None:
    for full_name in SOURCE_TABLE_CANDIDATES:
        if not table_exists(cur, full_name):
            print(f"market_source={full_name} exists=0")
            continue

        columns = table_columns(cur, full_name)

        symbol_col = pick_column(columns, SYMBOL_COLUMNS)
        timeframe_col = pick_column(columns, TIMEFRAME_COLUMNS)
        ts_col = pick_column(columns, TS_COLUMNS, require_time=True)
        close_col = pick_column(columns, CLOSE_COLUMNS)
        volume_col = pick_column(columns, VOLUME_COLUMNS)

        print(
            f"market_source={full_name} exists=1 "
            f"symbol_col={symbol_col} timeframe_col={timeframe_col} "
            f"ts_col={ts_col} close_col={close_col} volume_col={volume_col}"
        )

        if symbol_col and ts_col:
            schema, name = full_name.split(".", 1)
            return MarketSource(
                table=full_name,
                schema=schema,
                name=name,
                symbol_col=symbol_col,
                timeframe_col=timeframe_col,
                ts_col=ts_col,
                close_col=close_col,
                volume_col=volume_col,
            )

    return None


def query_latest(cur, source: MarketSource, symbol_value: str, timeframe_value: str, exact_timeframe: bool) -> dict:
    where_parts = [sql.SQL("{} = %s").format(sql.Identifier(source.symbol_col))]
    params: list[object] = [symbol_value]

    if exact_timeframe and source.timeframe_col and timeframe_value:
        where_parts.append(sql.SQL("{} = %s").format(sql.Identifier(source.timeframe_col)))
        params.append(timeframe_value)

    where_sql = sql.SQL(" AND ").join(where_parts)

    query = sql.SQL("""
        SELECT
            count(*) AS bars_total,
            max({ts_col})::timestamptz AS latest_bar_ts,
            extract(epoch FROM (now() - max({ts_col})::timestamptz))::int AS market_data_age_sec
        FROM {schema}.{table}
        WHERE {where_sql};
    """).format(
        ts_col=sql.Identifier(source.ts_col),
        schema=sql.Identifier(source.schema),
        table=sql.Identifier(source.name),
        where_sql=where_sql,
    )

    cur.execute(query, params)
    summary = dict(cur.fetchone())

    bars_total = int(summary["bars_total"] or 0)

    result = {
        "bars_total": bars_total,
        "latest_bar_ts": summary["latest_bar_ts"],
        "market_data_age_sec": summary["market_data_age_sec"],
        "latest_close": None,
        "latest_volume": None,
        "market_timeframe": timeframe_value if exact_timeframe else "ANY",
    }

    if bars_total <= 0:
        return result

    select_cols = [
        sql.SQL("{}::timestamptz AS latest_bar_ts").format(sql.Identifier(source.ts_col)),
    ]

    if source.close_col:
        select_cols.append(sql.SQL("{}::numeric AS latest_close").format(sql.Identifier(source.close_col)))
    else:
        select_cols.append(sql.SQL("NULL::numeric AS latest_close"))

    if source.volume_col:
        select_cols.append(sql.SQL("{}::numeric AS latest_volume").format(sql.Identifier(source.volume_col)))
    else:
        select_cols.append(sql.SQL("NULL::numeric AS latest_volume"))

    latest_query = sql.SQL("""
        SELECT {select_cols}
        FROM {schema}.{table}
        WHERE {where_sql}
        ORDER BY {ts_col} DESC NULLS LAST
        LIMIT 1;
    """).format(
        select_cols=sql.SQL(", ").join(select_cols),
        schema=sql.Identifier(source.schema),
        table=sql.Identifier(source.name),
        where_sql=where_sql,
        ts_col=sql.Identifier(source.ts_col),
    )

    cur.execute(latest_query, params)
    latest = dict(cur.fetchone())

    result["latest_close"] = latest["latest_close"]
    result["latest_volume"] = latest["latest_volume"]

    return result


def classify(source: MarketSource | None, bars_total: int, age_sec) -> tuple[str, str, str, str]:
    if source is None:
        return (
            "NO_MARKET_SOURCE",
            "NOT_BOUND",
            "Не найдена таблица рыночных баров с колонками symbol и timestamp.",
            "Подключить market_bars/feed к Paper Edge Discovery.",
        )

    if bars_total <= 0:
        return (
            "NO_BARS_FOR_CANDIDATE",
            "NO_BARS",
            "Источник рыночных данных найден, но по кандидату нет баров.",
            "Проверить символ, timeframe и backfill market_bars.",
        )

    if age_sec is None:
        return (
            "UNKNOWN_AGE",
            "BOUND_WITH_UNKNOWN_FRESHNESS",
            "Бары найдены, но возраст данных не определён.",
            "Проверить timestamp-колонку источника.",
        )

    if int(age_sec) <= FRESH_AFTER_SEC:
        return (
            "FRESH_MARKET_DATA",
            "BOUND_FRESH",
            "Кандидат привязан к свежим рыночным данным.",
            "Использовать market data в следующем этапе discovery.",
        )

    return (
        "STALE_MARKET_DATA",
        "BOUND_STALE",
        f"Рыночные данные найдены, но устарели: age_sec={age_sec}.",
        "Проверить поток market bars и актуальность backfill.",
    )


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1 ===")

            source = discover_market_source(cur)

            cur.execute("""
                SELECT
                    candidate_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side
                FROM marketcore_ui.paper_edge_research_candidates_v1
                ORDER BY candidate_rank
                LIMIT 50;
            """)
            candidates = [dict(r) for r in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.paper_edge_market_data_binding_v1;")

            for idx, row in enumerate(candidates, start=1):
                symbol_value = str(row.get("symbol") or "")
                timeframe_value = str(row.get("timeframe") or "")

                market_symbol = symbol_value
                market_timeframe = timeframe_value
                bars_total = 0
                latest_bar_ts = None
                latest_close = None
                latest_volume = None
                age_sec = None

                if source is not None:
                    latest = query_latest(
                        cur=cur,
                        source=source,
                        symbol_value=symbol_value,
                        timeframe_value=timeframe_value,
                        exact_timeframe=True,
                    )

                    if latest["bars_total"] <= 0 and source.timeframe_col:
                        latest = query_latest(
                            cur=cur,
                            source=source,
                            symbol_value=symbol_value,
                            timeframe_value=timeframe_value,
                            exact_timeframe=False,
                        )

                    bars_total = int(latest["bars_total"] or 0)
                    latest_bar_ts = latest["latest_bar_ts"]
                    latest_close = latest["latest_close"]
                    latest_volume = latest["latest_volume"]
                    age_sec = latest["market_data_age_sec"]
                    market_timeframe = str(latest["market_timeframe"] or timeframe_value)

                market_data_status, binding_status, binding_reason, recommended_action = classify(
                    source=source,
                    bars_total=bars_total,
                    age_sec=age_sec,
                )

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_edge_market_data_binding_v1 (
                        binding_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        market_symbol,
                        market_timeframe,
                        bars_source_table,
                        bars_total,
                        latest_bar_ts,
                        latest_close,
                        latest_volume,
                        market_data_age_sec,
                        market_data_status,
                        binding_status,
                        binding_reason,
                        recommended_action,
                        source_candidate_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,now(),%s
                    );
                """, (
                    idx,
                    symbol_value,
                    row.get("strategy") or "",
                    timeframe_value,
                    row.get("side") or "",
                    market_symbol,
                    market_timeframe,
                    source.table if source else "",
                    bars_total,
                    latest_bar_ts,
                    latest_close,
                    latest_volume,
                    age_sec,
                    market_data_status,
                    binding_status,
                    binding_reason,
                    recommended_action,
                    row.get("candidate_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_market_data_binding_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT market_data_status, count(*) AS rows
                FROM marketcore_ui.paper_edge_market_data_binding_v1
                GROUP BY market_data_status
                ORDER BY market_data_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    print(f"market_source_table={source.table if source else 'NONE'}")
    for status_row in status_rows:
        print(f"market_data_status_{status_row['market_data_status']}={status_row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-edge-market-data-binding' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-edge-market-data-binding":
                limit = int(q.get("limit", ["50"])[0])
                rows = fetch_all("""
                    SELECT
                        binding_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        market_symbol,
                        market_timeframe,
                        bars_source_table,
                        bars_total,
                        latest_bar_ts,
                        latest_close,
                        latest_volume,
                        market_data_age_sec,
                        market_data_status,
                        binding_status,
                        binding_reason,
                        recommended_action,
                        source_candidate_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_market_data_binding_v1
                    ORDER BY binding_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_market_data_binding_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_discovery_market_data_binding_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_edge_market_data_binding.py <<'PY'
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
        return "<p>Привязка рыночных данных пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("binding_rank", "")))}</td>
            <td>{escape(str(row.get("symbol", "")))}</td>
            <td>{escape(str(row.get("strategy", "")))}</td>
            <td>{escape(str(row.get("timeframe", "")))}</td>
            <td>{escape(str(row.get("bars_source_table", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("bars_total"), 0))}</td>
            <td>{escape(ctx.formatter.datetime(row.get("latest_bar_ts")))}</td>
            <td>{escape(ctx.formatter.number(row.get("latest_close"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("market_data_age_sec"), 0))}</td>
            <td>{escape(str(row.get("market_data_status", "")))}</td>
            <td>{escape(str(row.get("binding_status", "")))}</td>
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
                <th>Источник</th>
                <th>Баров</th>
                <th>Последний бар</th>
                <th>Close</th>
                <th>Age sec</th>
                <th>Market Status</th>
                <th>Binding</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeMarketDataBindingPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-market-data-binding",
            title="Привязка рыночных данных",
            icon="◎",
            menu_order=21,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-edge-market-data-binding?limit=50")
        rows = payload.get("data") or []

        fresh = sum(1 for row in rows if row.get("market_data_status") == "FRESH_MARKET_DATA")
        stale = sum(1 for row in rows if row.get("market_data_status") == "STALE_MARKET_DATA")
        no_bars = sum(1 for row in rows if row.get("market_data_status") == "NO_BARS_FOR_CANDIDATE")
        no_source = sum(1 for row in rows if row.get("market_data_status") == "NO_MARKET_SOURCE")

        return f"""
        <section class="card">
            <h2>Привязка рыночных данных</h2>
            <p>Показывает, есть ли свежие market bars для кандидатов Paper Edge Discovery.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_edge_market_data_binding_v1.</p>
            <p><a href="/paper-edge-discovery">← Поиск преимущества</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Кандидатов", ctx.formatter.number(len(rows), 0))}
            {_metric("Fresh", ctx.formatter.number(fresh, 0))}
            {_metric("Stale", ctx.formatter.number(stale, 0))}
            {_metric("No Bars", ctx.formatter.number(no_bars, 0))}
            {_metric("No Source", ctx.formatter.number(no_source, 0))}
        </div>

        <section class="card">
            <h2>Market Data Binding</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Вывод</h2>
            <p>Если здесь STALE/NO_BARS/NO_SOURCE, значит Paper Edge Discovery пока опирается на накопленные paper/research данные, а не на свежий market feed.</p>
            <p>Следующий шаг: PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1.</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/pages/paper_edge_discovery.py")
s = p.read_text()

if "PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1" not in s:
    block = '''
        <section class="card">
            <h2>Рыночные данные</h2>
            <p>Проверить, есть ли свежие market bars для кандидатов и почему сейчас видны старые paper-кандидаты.</p>
            <p><a href="/paper-edge-market-data-binding">Открыть привязку рыночных данных</a></p>
            <p>PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1</p>
        </section>
'''
    needle = '        <section class="card">\n            <h2>Next Action</h2>'
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

if '"/paper-edge-market-data-binding"' not in s:
    s = s.replace(
        '    "/paper-edge-discovery": "Поиск преимущества",\n',
        '    "/paper-edge-discovery": "Поиск преимущества",\n'
        '    "/paper-edge-market-data-binding": "Рыночные данные кандидатов",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/route_groups.py")
s = p.read_text()

if '"/paper-edge-market-data-binding"' not in s:
    s = s.replace(
        '            "/paper-edge-discovery",\n',
        '            "/paper-edge-discovery",\n'
        '            "/paper-edge-market-data-binding",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperEdgeMarketDataBindingPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_edge_market_data_binding import PaperEdgeMarketDataBindingPage\n",
    )

if "PaperEdgeMarketDataBindingPage()," not in s:
    if "PaperEdgeDiscoveryPage()," in s:
        s = s.replace(
            "PaperEdgeDiscoveryPage(),",
            "PaperEdgeDiscoveryPage(),\n    PaperEdgeMarketDataBindingPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperEdgeMarketDataBindingPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_edge_discovery_market_data_binding_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1 ==="

scripts/apply_paper_edge_market_data_binding_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_data_binding_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_market_data_binding.py \
  src/marketcore/presentation/pages/paper_edge_discovery.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_market_data_binding.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/market_data_binding_candidates_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_binding_v1.py \
  | tee /tmp/paper_edge_market_data_binding_builder_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_READY" \
  /tmp/paper_edge_market_data_binding_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20595 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_market_data_binding_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20580 KG_API_BASE_URL=http://127.0.0.1:20595 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/market_data_binding_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20595/api/kg/v1/paper-edge-market-data-binding?limit=20" \
  > /tmp/paper_edge_market_data_binding_api_v1.json

curl -fsS "http://127.0.0.1:20580/paper-edge-market-data-binding" \
  > /tmp/paper_edge_market_data_binding_page_v1.html

curl -fsS "http://127.0.0.1:20580/paper-edge-discovery" \
  > /tmp/paper_edge_discovery_market_data_link_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_market_data_binding_api_v1.json
grep -q '"market_data_status"' /tmp/paper_edge_market_data_binding_api_v1.json
grep -q '"binding_status"' /tmp/paper_edge_market_data_binding_api_v1.json
grep -q '"bars_source_table"' /tmp/paper_edge_market_data_binding_api_v1.json
grep -q '"recommended_action"' /tmp/paper_edge_market_data_binding_api_v1.json

grep -q "Привязка рыночных данных" /tmp/paper_edge_market_data_binding_page_v1.html
grep -q "Market Data Binding" /tmp/paper_edge_market_data_binding_page_v1.html
grep -q "marketcore_ui.paper_edge_market_data_binding_v1" /tmp/paper_edge_market_data_binding_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1" /tmp/paper_edge_market_data_binding_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_market_data_binding_page_v1.html

grep -q "Рыночные данные" /tmp/paper_edge_discovery_market_data_link_v1.html
grep -q "paper-edge-market-data-binding" /tmp/paper_edge_discovery_market_data_link_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1" /tmp/paper_edge_discovery_market_data_link_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_binding_v1;")
test "$rows" -gt 0

psql -d finam_core -c "
SELECT
    market_data_status,
    binding_status,
    count(*) AS rows
FROM marketcore_ui.paper_edge_market_data_binding_v1
GROUP BY market_data_status, binding_status
ORDER BY market_data_status, binding_status;
"

echo "market_data_binding_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_market_data_binding_v1.sh

scripts/test_paper_edge_discovery_market_data_binding_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1_OK"
