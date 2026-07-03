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
    "marketcore.market_snapshot_v1",
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
            "Построить MARKET_MODEL_V1: marketcore.market_snapshot_v1.",
        )

    if bars_total <= 0:
        return (
            "NO_BARS_FOR_CANDIDATE",
            "NO_BARS",
            "Источник рыночных данных найден, но по кандидату нет баров.",
            "Проверить symbol/timeframe в marketcore.market_snapshot_v1 и обновить MARKET_MODEL_V1.",
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
                    queue_rank AS candidate_rank,
                    symbol,
                    recommended_strategy_family AS strategy,
                    timeframe,
                    ''::text AS side
                FROM marketcore_ui.market_universe_research_queue_v1
                ORDER BY queue_rank
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
