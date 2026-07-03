#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1 ==="

mkdir -p sql/marketcore_ui src/scripts scripts src/marketcore/presentation/pages

cat > sql/marketcore_ui/029_paper_edge_market_data_freshness_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_data_freshness_v1 (
    freshness_rank INTEGER PRIMARY KEY,
    row_type TEXT NOT NULL DEFAULT '',

    candidate_symbol TEXT NOT NULL DEFAULT '',
    candidate_strategy TEXT NOT NULL DEFAULT '',
    candidate_timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    market_symbol TEXT NOT NULL DEFAULT '',
    market_timeframe TEXT NOT NULL DEFAULT '',
    source_table TEXT NOT NULL DEFAULT '',

    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_bar_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    market_data_age_sec INTEGER,

    freshness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    binding_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_data_freshness_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_DATA_FRESHNESS_SCHEMA_V1_READY' AS verdict;
SQL

cat > scripts/apply_paper_edge_market_data_freshness_v1.sh <<'SH_APPLY'
#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql \
  -v ON_ERROR_STOP=1 \
  -d finam_core \
  -f sql/marketcore_ui/029_paper_edge_market_data_freshness_v1.sql
SH_APPLY

chmod +x scripts/apply_paper_edge_market_data_freshness_v1.sh

cat > src/scripts/build_paper_edge_market_data_freshness_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

import psycopg2
import psycopg2.extras
from psycopg2 import sql

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1"
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
        if candidate.lower() not in lower_map:
            continue

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


def classify_source_age(age_sec) -> tuple[str, str, str]:
    if age_sec is None:
        return (
            "SOURCE_UNKNOWN_AGE",
            "Возраст последнего бара не определён.",
            "Проверить timestamp-колонку источника market bars.",
        )

    if int(age_sec) <= FRESH_AFTER_SEC:
        return (
            "SOURCE_FRESH",
            "Источник рыночных данных обновляется и содержит свежие бары.",
            "Использовать market feed для следующего этапа Paper Edge Discovery.",
        )

    return (
        "SOURCE_STALE",
        f"Источник содержит бары, но последний бар устарел: age_sec={age_sec}.",
        "Проверить поток market bars, backfill и расписание обновления.",
    )


def classify_candidate_binding(row: dict) -> tuple[str, str, str]:
    market_data_status = str(row.get("market_data_status") or "UNKNOWN")
    binding_status = str(row.get("binding_status") or "UNKNOWN")

    if market_data_status == "FRESH_MARKET_DATA":
        return (
            "CANDIDATE_BOUND_FRESH",
            "Кандидат привязан к свежим рыночным данным.",
            "Можно использовать market data в следующем этапе discovery.",
        )

    if market_data_status == "STALE_MARKET_DATA":
        return (
            "CANDIDATE_BOUND_STALE",
            "Кандидат имеет market bars, но они устарели.",
            "Проверить актуальность market_bars для этого инструмента.",
        )

    if market_data_status == "NO_BARS_FOR_CANDIDATE" or binding_status == "NO_BARS":
        return (
            "CANDIDATE_NO_BARS",
            "По текущему candidate symbol/timeframe нет баров в market source.",
            "Проверить соответствие symbol/timeframe, добавить alias/continuous mapping или backfill.",
        )

    if market_data_status == "NO_MARKET_SOURCE":
        return (
            "NO_MARKET_SOURCE",
            "Не найден источник рыночных баров.",
            "Подключить market_bars/feed.",
        )

    return (
        "CANDIDATE_BINDING_UNKNOWN",
        "Статус привязки кандидата к market data не определён.",
        "Проверить paper_edge_market_data_binding_v1.",
    )


def fetch_source_latest_rows(cur, source: MarketSource, limit: int = 50) -> list[dict]:
    if source.timeframe_col:
        tf_expr = sql.SQL("{}::text").format(sql.Identifier(source.timeframe_col))
        group_cols = sql.SQL("{symbol_col}, {tf_col}").format(
            symbol_col=sql.Identifier(source.symbol_col),
            tf_col=sql.Identifier(source.timeframe_col),
        )
    else:
        tf_expr = sql.SQL("''::text")
        group_cols = sql.SQL("{symbol_col}").format(
            symbol_col=sql.Identifier(source.symbol_col),
        )

    query = sql.SQL("""
        SELECT
            {symbol_col}::text AS market_symbol,
            {tf_expr} AS market_timeframe,
            count(*)::int AS bars_total,
            max({ts_col})::timestamptz AS latest_bar_ts,
            extract(epoch FROM (now() - max({ts_col})::timestamptz))::int AS market_data_age_sec
        FROM {schema}.{table}
        GROUP BY {group_cols}
        ORDER BY max({ts_col}) DESC NULLS LAST
        LIMIT %s;
    """).format(
        symbol_col=sql.Identifier(source.symbol_col),
        tf_expr=tf_expr,
        ts_col=sql.Identifier(source.ts_col),
        schema=sql.Identifier(source.schema),
        table=sql.Identifier(source.name),
        group_cols=group_cols,
    )

    cur.execute(query, (limit,))
    return [dict(r) for r in cur.fetchall()]


def fetch_latest_price(cur, source: MarketSource, market_symbol: str, market_timeframe: str):
    select_parts = []

    if source.close_col:
        select_parts.append(sql.SQL("{}::numeric AS latest_close").format(sql.Identifier(source.close_col)))
    else:
        select_parts.append(sql.SQL("NULL::numeric AS latest_close"))

    if source.volume_col:
        select_parts.append(sql.SQL("{}::numeric AS latest_volume").format(sql.Identifier(source.volume_col)))
    else:
        select_parts.append(sql.SQL("NULL::numeric AS latest_volume"))

    where_parts = [sql.SQL("{} = %s").format(sql.Identifier(source.symbol_col))]
    params: list[object] = [market_symbol]

    if source.timeframe_col and market_timeframe:
        where_parts.append(sql.SQL("{} = %s").format(sql.Identifier(source.timeframe_col)))
        params.append(market_timeframe)

    query = sql.SQL("""
        SELECT {select_parts}
        FROM {schema}.{table}
        WHERE {where_sql}
        ORDER BY {ts_col} DESC NULLS LAST
        LIMIT 1;
    """).format(
        select_parts=sql.SQL(", ").join(select_parts),
        schema=sql.Identifier(source.schema),
        table=sql.Identifier(source.name),
        where_sql=sql.SQL(" AND ").join(where_parts),
        ts_col=sql.Identifier(source.ts_col),
    )

    cur.execute(query, params)
    row = cur.fetchone()
    if not row:
        return None, None

    return row["latest_close"], row["latest_volume"]


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1 ===")

            source = discover_market_source(cur)

            cur.execute("DELETE FROM marketcore_ui.paper_edge_market_data_freshness_v1;")

            rank = 0

            cur.execute("""
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
                    binding_status
                FROM marketcore_ui.paper_edge_market_data_binding_v1
                ORDER BY binding_rank
                LIMIT 50;
            """)
            bindings = [dict(r) for r in cur.fetchall()]

            for row in bindings:
                rank += 1
                freshness_status, diagnosis, action = classify_candidate_binding(row)

                cur.execute("""
                    INSERT INTO marketcore_ui.paper_edge_market_data_freshness_v1 (
                        freshness_rank,
                        row_type,
                        candidate_symbol,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        market_symbol,
                        market_timeframe,
                        source_table,
                        bars_total,
                        latest_bar_ts,
                        latest_close,
                        latest_volume,
                        market_data_age_sec,
                        freshness_status,
                        binding_status,
                        diagnosis,
                        recommended_action,
                        source_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,'CANDIDATE_BINDING',%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                """, (
                    rank,
                    row.get("symbol") or "",
                    row.get("strategy") or "",
                    row.get("timeframe") or "",
                    row.get("side") or "",
                    row.get("market_symbol") or "",
                    row.get("market_timeframe") or "",
                    row.get("bars_source_table") or "",
                    row.get("bars_total") or 0,
                    row.get("latest_bar_ts"),
                    row.get("latest_close"),
                    row.get("latest_volume"),
                    row.get("market_data_age_sec"),
                    freshness_status,
                    row.get("binding_status") or "",
                    diagnosis,
                    action,
                    row.get("binding_rank"),
                    SOURCE_VERSION,
                    build_id,
                ))

            if source is None:
                rank += 1
                cur.execute("""
                    INSERT INTO marketcore_ui.paper_edge_market_data_freshness_v1 (
                        freshness_rank,
                        row_type,
                        source_table,
                        freshness_status,
                        binding_status,
                        diagnosis,
                        recommended_action,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,'SOURCE_SUMMARY','',
                        'NO_MARKET_SOURCE','NOT_BOUND',
                        'Не найден источник рыночных баров.',
                        'Подключить market_bars/feed.',
                        %s,now(),%s
                    );
                """, (rank, SOURCE_VERSION, build_id))
            else:
                latest_rows = fetch_source_latest_rows(cur, source, limit=50)

                for source_row in latest_rows:
                    rank += 1

                    latest_close, latest_volume = fetch_latest_price(
                        cur=cur,
                        source=source,
                        market_symbol=str(source_row.get("market_symbol") or ""),
                        market_timeframe=str(source_row.get("market_timeframe") or ""),
                    )

                    freshness_status, diagnosis, action = classify_source_age(
                        source_row.get("market_data_age_sec")
                    )

                    cur.execute("""
                        INSERT INTO marketcore_ui.paper_edge_market_data_freshness_v1 (
                            freshness_rank,
                            row_type,
                            market_symbol,
                            market_timeframe,
                            source_table,
                            bars_total,
                            latest_bar_ts,
                            latest_close,
                            latest_volume,
                            market_data_age_sec,
                            freshness_status,
                            binding_status,
                            diagnosis,
                            recommended_action,
                            source_version,
                            refreshed_at,
                            build_id
                        )
                        VALUES (
                            %s,'SOURCE_LATEST',%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,'SOURCE',
                            %s,%s,%s,now(),%s
                        );
                    """, (
                        rank,
                        source_row.get("market_symbol") or "",
                        source_row.get("market_timeframe") or "",
                        source.table,
                        source_row.get("bars_total") or 0,
                        source_row.get("latest_bar_ts"),
                        latest_close,
                        latest_volume,
                        source_row.get("market_data_age_sec"),
                        freshness_status,
                        diagnosis,
                        action,
                        SOURCE_VERSION,
                        build_id,
                    ))

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.paper_edge_market_data_freshness_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT row_type, freshness_status, count(*) AS rows
                FROM marketcore_ui.paper_edge_market_data_freshness_v1
                GROUP BY row_type, freshness_status
                ORDER BY row_type, freshness_status;
            """)
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    print(f"market_source_table={source.table if source else 'NONE'}")
    for status_row in status_rows:
        print(
            f"freshness row_type={status_row['row_type']} "
            f"status={status_row['freshness_status']} "
            f"rows={status_row['rows']}"
        )
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY")


if __name__ == "__main__":
    main()
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/api/serve_knowledge_graph_api_v1.py")
s = p.read_text()

if '/api/kg/v1/paper-edge-market-data-freshness' not in s:
    marker = '            self.send_json(404, response("NOT_FOUND", {}, {"path": path}))\n'
    if marker not in s:
        raise SystemExit("API 404 marker not found")

    block = '''
            if path == "/api/kg/v1/paper-edge-market-data-freshness":
                limit = int(q.get("limit", ["100"])[0])
                rows = fetch_all("""
                    SELECT
                        freshness_rank,
                        row_type,
                        candidate_symbol,
                        candidate_strategy,
                        candidate_timeframe,
                        side,
                        market_symbol,
                        market_timeframe,
                        source_table,
                        bars_total,
                        latest_bar_ts,
                        latest_close,
                        latest_volume,
                        market_data_age_sec,
                        freshness_status,
                        binding_status,
                        diagnosis,
                        recommended_action,
                        source_rank,
                        refreshed_at
                    FROM marketcore_ui.paper_edge_market_data_freshness_v1
                    ORDER BY freshness_rank
                    LIMIT %s;
                """, (limit,))
                self.send_json(200, response("OK", rows, {
                    "source": "marketcore_ui.paper_edge_market_data_freshness_v1",
                    "ui_direct_sql": 0,
                    "logic": "paper_edge_discovery_market_data_freshness_v1"
                }))
                return

'''
    s = s.replace(marker, block + marker)

p.write_text(s)
PY

cat > src/marketcore/presentation/pages/paper_edge_market_data_freshness.py <<'PY'
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
        return "<p>Freshness-диагностика пуста.</p>"

    body = ""
    for row in rows:
        body += f"""
        <tr>
            <td>{escape(str(row.get("freshness_rank", "")))}</td>
            <td>{escape(str(row.get("row_type", "")))}</td>
            <td>{escape(str(row.get("candidate_symbol", "")))}</td>
            <td>{escape(str(row.get("market_symbol", "")))}</td>
            <td>{escape(str(row.get("market_timeframe", "")))}</td>
            <td>{escape(str(row.get("source_table", "")))}</td>
            <td>{escape(ctx.formatter.number(row.get("bars_total"), 0))}</td>
            <td>{escape(ctx.formatter.datetime(row.get("latest_bar_ts")))}</td>
            <td>{escape(ctx.formatter.number(row.get("latest_close"), 4))}</td>
            <td>{escape(ctx.formatter.number(row.get("market_data_age_sec"), 0))}</td>
            <td>{escape(str(row.get("freshness_status", "")))}</td>
            <td>{escape(str(row.get("diagnosis", "")))}</td>
            <td>{escape(str(row.get("recommended_action", "")))}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Тип</th>
                <th>Кандидат</th>
                <th>Market Symbol</th>
                <th>TF</th>
                <th>Источник</th>
                <th>Баров</th>
                <th>Последний бар</th>
                <th>Close</th>
                <th>Age sec</th>
                <th>Status</th>
                <th>Диагноз</th>
                <th>Действие</th>
            </tr>
        </thead>
        <tbody>{body}</tbody>
    </table>
    """


class PaperEdgeMarketDataFreshnessPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-edge-market-data-freshness",
            title="Свежесть рыночных данных",
            icon="◎",
            menu_order=22,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/paper-edge-market-data-freshness?limit=100")
        rows = payload.get("data") or []

        candidate_no_bars = sum(1 for row in rows if row.get("freshness_status") == "CANDIDATE_NO_BARS")
        source_fresh = sum(1 for row in rows if row.get("freshness_status") == "SOURCE_FRESH")
        source_stale = sum(1 for row in rows if row.get("freshness_status") == "SOURCE_STALE")
        no_source = sum(1 for row in rows if row.get("freshness_status") == "NO_MARKET_SOURCE")

        return f"""
        <section class="card">
            <h2>Свежесть рыночных данных</h2>
            <p>Диагностика показывает две вещи: есть ли свежий market feed вообще и совпадают ли Paper-кандидаты с market_bars.</p>
            <p>Источник: Knowledge Graph API → marketcore_ui.paper_edge_market_data_freshness_v1.</p>
            <p><a href="/paper-edge-market-data-binding">← Привязка рыночных данных</a></p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;">
            {_metric("Всего строк", ctx.formatter.number(len(rows), 0))}
            {_metric("Candidate No Bars", ctx.formatter.number(candidate_no_bars, 0))}
            {_metric("Source Fresh", ctx.formatter.number(source_fresh, 0))}
            {_metric("Source Stale", ctx.formatter.number(source_stale, 0))}
            {_metric("No Source", ctx.formatter.number(no_source, 0))}
        </div>

        <section class="card">
            <h2>Freshness Matrix</h2>
            {_table(rows, ctx)}
        </section>

        <section class="card">
            <h2>Вывод</h2>
            <p>Если SOURCE_FRESH есть, но CANDIDATE_NO_BARS=20, проблема не в отсутствии market feed, а в несовпадении символов/timeframe кандидатов и market_bars.</p>
            <p>Следующий шаг: PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1.</p>
        </section>
        """
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/pages/paper_edge_market_data_binding.py")
s = p.read_text()

if "PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1" not in s:
    print("WARN expected marker already missing or page format changed")

# Link to freshness page if not present.
if "/paper-edge-market-data-freshness" not in s:
    block = '''
        <section class="card">
            <h2>Freshness</h2>
            <p><a href="/paper-edge-market-data-freshness">Открыть диагностику свежести рыночных данных</a></p>
            <p>PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1</p>
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

if '"/paper-edge-market-data-freshness"' not in s:
    s = s.replace(
        '    "/paper-edge-market-data-binding": "Рыночные данные кандидатов",\n',
        '    "/paper-edge-market-data-binding": "Рыночные данные кандидатов",\n'
        '    "/paper-edge-market-data-freshness": "Свежесть рыночных данных",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/route_groups.py")
s = p.read_text()

if '"/paper-edge-market-data-freshness"' not in s:
    s = s.replace(
        '            "/paper-edge-market-data-binding",\n',
        '            "/paper-edge-market-data-binding",\n'
        '            "/paper-edge-market-data-freshness",\n',
    )

p.write_text(s)
PY

python <<'PY'
from pathlib import Path

p = Path("src/marketcore/presentation/registry.py")
s = p.read_text()

if "PaperEdgeMarketDataFreshnessPage" not in s:
    s = s.replace(
        "from marketcore.presentation.pages.home import HomePage\n",
        "from marketcore.presentation.pages.home import HomePage\n"
        "from marketcore.presentation.pages.paper_edge_market_data_freshness import PaperEdgeMarketDataFreshnessPage\n",
    )

if "PaperEdgeMarketDataFreshnessPage()," not in s:
    if "PaperEdgeMarketDataBindingPage()," in s:
        s = s.replace(
            "PaperEdgeMarketDataBindingPage(),",
            "PaperEdgeMarketDataBindingPage(),\n    PaperEdgeMarketDataFreshnessPage(),",
        )
    else:
        s = s.replace(
            "HomePage(),",
            "HomePage(),\n    PaperEdgeMarketDataFreshnessPage(),",
        )

p.write_text(s)
PY

cat > scripts/test_paper_edge_discovery_market_data_freshness_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1 ==="

scripts/apply_paper_edge_market_data_freshness_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_paper_edge_market_data_freshness_v1.py \
  src/marketcore/api/serve_knowledge_graph_api_v1.py \
  src/marketcore/presentation/pages/paper_edge_market_data_freshness.py \
  src/marketcore/presentation/pages/paper_edge_market_data_binding.py \
  src/marketcore/presentation/registry.py \
  src/marketcore/presentation/app.py

if grep -R "psycopg2\|DATABASE_URL\|SELECT " -n src/marketcore/presentation/pages/paper_edge_market_data_freshness.py; then
  echo "FORBIDDEN_DIRECT_DB_ACCESS_IN_UI_PAGE"
  exit 1
fi

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_discovery_research_candidates_v1.py \
  > /tmp/freshness_candidates_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_binding_v1.py \
  > /tmp/freshness_binding_builder_v1.txt

sudo -u postgres env \
  DATABASE_URL=postgresql:///finam_core \
  PYTHONPATH=src \
  /opt/finam-core/venv/bin/python src/scripts/build_paper_edge_market_data_freshness_v1.py \
  | tee /tmp/paper_edge_market_data_freshness_builder_v1.txt

grep -q "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY" \
  /tmp/paper_edge_market_data_freshness_builder_v1.txt

KG_API_HOST=127.0.0.1 KG_API_PORT=20695 DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/marketcore/api/serve_knowledge_graph_api_v1.py > /tmp/kg_api_market_data_freshness_v1.log 2>&1 &
api_pid=$!

MARKETCORE_UI_HOST=127.0.0.1 MARKETCORE_UI_PORT=20680 KG_API_BASE_URL=http://127.0.0.1:20695 PYTHONPATH=src \
python src/marketcore/presentation/app.py > /tmp/market_data_freshness_ui_v1.log 2>&1 &
ui_pid=$!

cleanup() {
  kill "$ui_pid" >/dev/null 2>&1 || true
  kill "$api_pid" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2

curl -fsS "http://127.0.0.1:20695/api/kg/v1/paper-edge-market-data-freshness?limit=100" \
  > /tmp/paper_edge_market_data_freshness_api_v1.json

curl -fsS "http://127.0.0.1:20680/paper-edge-market-data-freshness" \
  > /tmp/paper_edge_market_data_freshness_page_v1.html

curl -fsS "http://127.0.0.1:20680/paper-edge-market-data-binding" \
  > /tmp/paper_edge_market_data_binding_freshness_link_v1.html

grep -q '"status": "OK"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"row_type"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"freshness_status"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"diagnosis"' /tmp/paper_edge_market_data_freshness_api_v1.json
grep -q '"recommended_action"' /tmp/paper_edge_market_data_freshness_api_v1.json

grep -q "Свежесть рыночных данных" /tmp/paper_edge_market_data_freshness_page_v1.html
grep -q "Freshness Matrix" /tmp/paper_edge_market_data_freshness_page_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1" /tmp/paper_edge_market_data_freshness_page_v1.html
grep -q "MARKETCORE_UI_SHELL_V1" /tmp/paper_edge_market_data_freshness_page_v1.html

grep -q "paper-edge-market-data-freshness" /tmp/paper_edge_market_data_binding_freshness_link_v1.html
grep -q "PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1" /tmp/paper_edge_market_data_binding_freshness_link_v1.html

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1;")
candidate_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1 WHERE row_type='CANDIDATE_BINDING';")
source_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.paper_edge_market_data_freshness_v1 WHERE row_type='SOURCE_LATEST';")

test "$rows" -gt 0
test "$candidate_rows" -gt 0

psql -d finam_core -c "
SELECT
    row_type,
    freshness_status,
    count(*) AS rows
FROM marketcore_ui.paper_edge_market_data_freshness_v1
GROUP BY row_type, freshness_status
ORDER BY row_type, freshness_status;
"

echo "market_data_freshness_rows=$rows"
echo "candidate_binding_rows=$candidate_rows"
echo "source_latest_rows=$source_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_READY"
echo "VERDICT=TEST_PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_OK"
SH_TEST

chmod +x scripts/test_paper_edge_discovery_market_data_freshness_v1.sh

scripts/test_paper_edge_discovery_market_data_freshness_v1.sh

echo "VERDICT=BUILD_PAPER_EDGE_DISCOVERY_MARKET_DATA_FRESHNESS_V1_OK"
