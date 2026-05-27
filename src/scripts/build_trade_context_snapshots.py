from __future__ import annotations

import argparse
import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.trade_context_snapshot_repository import (
    TradeContextSnapshot,
    TradeContextSnapshotRepository,
)


def _json_or_empty(value: Any) -> dict[str, Any]:
    # Русский комментарий:
    # PostgreSQL jsonb в psycopg3 обычно уже приходит dict, но оставляем защиту от строки.
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _table_exists(conn: psycopg.Connection, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select exists (
                select 1
                from information_schema.tables
                where table_schema = 'public'
                  and table_name = %s
            )
            """,
            (table_name,),
        )
        row = cur.fetchone()
        if row is None:
            return False
        if isinstance(row, dict):
            return bool(next(iter(row.values())))
        return bool(row[0])


def _load_source_rows(database_url: str, symbol: str, limit: int) -> list[dict[str, Any]]:
    # Русский комментарий:
    # Базовый источник контекста — trade_attribution_v2.
    # Если его нет или по символу нет строк, используем trades как fallback.
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        if _table_exists(conn, "trade_attribution_v2"):
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select
                            coalesce(trade_id::text, id::text) as trade_id,
                            id as db_trade_id,
                            symbol,
                            coalesce(continuous_symbol, symbol) as continuous_symbol,
                            coalesce(strategy, '') as strategy,
                            coalesce(timeframe, '') as timeframe,
                            coalesce(side, '') as side,
                            qty,
                            price,
                            coalesce(reason, '') as reason,
                            coalesce(trade_source, 'paper') as source,
                            coalesce(ts, created_at, now()) as ts,
                            to_jsonb(t.*) as attribution
                        from trade_attribution_v2 t
                        where symbol = %s
                        order by coalesce(ts, created_at, now()) desc
                        limit %s
                        """,
                        (symbol, limit),
                    )
                    rows = [dict(r) for r in cur.fetchall()]
                    if rows:
                        return rows
            except Exception as exc:
                # Русский комментарий:
                # Если аналитическая таблица отличается по схеме, не валим research pipeline.
                # Переходим на базовую таблицу trades.
                conn.rollback()
                print(f"TRADE_CONTEXT_ATTRIBUTION_FALLBACK reason={type(exc).__name__}", flush=True)

        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    coalesce(fill_id, id::text) as trade_id,
                    id as db_trade_id,
                    symbol,
                    coalesce(continuous_symbol, symbol) as continuous_symbol,
                    coalesce(strategy, '') as strategy,
                    coalesce(timeframe, '') as timeframe,
                    side,
                    qty,
                    price,
                    coalesce(payload->>'reason', '') as reason,
                    coalesce(trade_source, 'paper') as source,
                    ts,
                    payload as attribution
                from trades
                where symbol = %s
                  and is_invalid = false
                order by ts desc
                limit %s
                """,
                (symbol, limit),
            )
            return [dict(r) for r in cur.fetchall()]


def _load_latest_context(database_url: str, table_name: str, symbol: str) -> dict[str, Any]:
    # Русский комментарий:
    # Подмешиваем последний доступный контекст по символу.
    # Если таблицы нет, возвращаем пустой словарь и не валим pipeline.
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        if not _table_exists(conn, table_name):
            return {}
        with conn.cursor() as cur:
            cur.execute(
                f"""
                select to_jsonb(t.*) as payload
                from {table_name} t
                where symbol = %s
                order by ctid desc
                limit 1
                """,
                (symbol,),
            )
            row = cur.fetchone()
            return _json_or_empty(row["payload"]) if row else {}


def build_snapshots(database_url: str, symbol: str, limit: int) -> list[TradeContextSnapshot]:
    source_rows = _load_source_rows(database_url, symbol, limit)

    risk_context = _load_latest_context(database_url, "trade_risk_context", symbol)
    exit_policy_context = _load_latest_context(database_url, "trade_exit_policy_context", symbol)
    feature_context = _load_latest_context(database_url, "feature_snapshots", symbol)

    items: list[TradeContextSnapshot] = []

    for row in source_rows:
        snapshot = {
            "attribution": _json_or_empty(row.get("attribution")),
            "risk_context": risk_context,
            "exit_policy_context": exit_policy_context,
            "feature_context": feature_context,
            "context_quality": {
                "has_attribution": bool(row.get("attribution")),
                "has_risk_context": bool(risk_context),
                "has_exit_policy_context": bool(exit_policy_context),
                "has_feature_context": bool(feature_context),
            },
        }

        items.append(
            TradeContextSnapshot(
                trade_id=str(row.get("trade_id") or ""),
                db_trade_id=row.get("db_trade_id"),
                run_id=None,
                symbol=str(row.get("symbol") or symbol),
                continuous_symbol=row.get("continuous_symbol"),
                strategy=str(row.get("strategy") or ""),
                timeframe=str(row.get("timeframe") or ""),
                side=row.get("side"),
                qty=row.get("qty"),
                price=row.get("price"),
                reason=row.get("reason"),
                source=row.get("source"),
                ts=row.get("ts"),
                snapshot=snapshot,
            )
        )

    return items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    database_url = build_psycopg_url()
    repo = TradeContextSnapshotRepository(database_url)

    if args.migrate:
        print("TRADE_CONTEXT_SNAPSHOTS_MIGRATE_SKIPPED reason=repository_writer_only", flush=True)

    items = build_snapshots(database_url=database_url, symbol=args.symbol, limit=args.limit)

    saved = 0
    if args.save:
        for item in items:
            if item.trade_id:
                repo.save(item)
                saved += 1

    full = sum(
        1
        for item in items
        if all((item.snapshot or {}).get("context_quality", {}).values())
    )
    partial = len(items) - full

    print(
        "TRADE_CONTEXT_SNAPSHOT_SUMMARY "
        f"symbol={args.symbol} total={len(items)} full={full} partial={partial} saved={saved}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
