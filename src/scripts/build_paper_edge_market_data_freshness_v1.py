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
