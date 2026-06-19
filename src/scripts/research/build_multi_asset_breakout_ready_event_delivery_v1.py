#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.notifications.telegram_signal_dispatcher import TelegramSignalDispatcher
from finam_core.notifications.telegram_signal_taxonomy import TelegramSignalMessage


@dataclass(frozen=True)
class ReadyEvent:
    row_id: int
    snapshot_id: int
    created_at: str
    symbol: str
    asset_class: str
    timeframe: str
    role: str
    close: Decimal | None
    prev_high: Decimal | None
    status: str


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_multi_asset_breakout_ready_delivery_v1 (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ready_row_id BIGINT NOT NULL UNIQUE,
                snapshot_id BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                asset_class TEXT,
                timeframe TEXT,
                role TEXT,
                ready_created_at TIMESTAMPTZ NOT NULL,
                close NUMERIC,
                prev_high NUMERIC,
                status TEXT,
                delivery_channel TEXT NOT NULL DEFAULT 'RADAR',
                delivery_status TEXT NOT NULL,
                delivery_reason TEXT NOT NULL,
                dry_run BOOLEAN NOT NULL DEFAULT TRUE,
                telegram_result_status TEXT,
                telegram_result_reason TEXT,
                runtime_allow BOOLEAN NOT NULL DEFAULT FALSE,
                execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                real_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_breakout_ready_delivery_v1_symbol_time
            ON analytics_multi_asset_breakout_ready_delivery_v1(symbol, timeframe, ready_created_at DESC)
            """
        )
    conn.commit()


def fetch_undelivered_ready_events(conn: psycopg.Connection, limit: int) -> list[ReadyEvent]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                r.id AS row_id,
                r.snapshot_id,
                r.created_at,
                r.symbol,
                r.asset_class,
                r.timeframe,
                r.role,
                r.close,
                r.prev_high,
                r.status
            FROM analytics_multi_asset_breakout_row_v1 r
            LEFT JOIN analytics_multi_asset_breakout_ready_delivery_v1 d
              ON d.ready_row_id = r.id
            WHERE r.status LIKE %(ready_pattern)s
              AND d.ready_row_id IS NULL
            ORDER BY r.created_at
            LIMIT %(limit)s
            """,
            {"limit": limit, "ready_pattern": "%BREAKOUT_READY%"},
        )
        return [
            ReadyEvent(
                row_id=int(row["row_id"]),
                snapshot_id=int(row["snapshot_id"]),
                created_at=str(row["created_at"]),
                symbol=str(row["symbol"]),
                asset_class=str(row["asset_class"]),
                timeframe=str(row["timeframe"]),
                role=str(row["role"]),
                close=row["close"],
                prev_high=row["prev_high"],
                status=str(row["status"]),
            )
            for row in cur.fetchall()
        ]


def save_delivery(
    conn: psycopg.Connection,
    event: ReadyEvent,
    *,
    delivery_status: str,
    delivery_reason: str,
    dry_run: bool,
    telegram_result_status: str | None,
    telegram_result_reason: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics_multi_asset_breakout_ready_delivery_v1 (
                ready_row_id,
                snapshot_id,
                symbol,
                asset_class,
                timeframe,
                role,
                ready_created_at,
                close,
                prev_high,
                status,
                delivery_channel,
                delivery_status,
                delivery_reason,
                dry_run,
                telegram_result_status,
                telegram_result_reason,
                runtime_allow,
                execution_enabled,
                real_trading_enabled
            )
            VALUES (
                %(ready_row_id)s,
                %(snapshot_id)s,
                %(symbol)s,
                %(asset_class)s,
                %(timeframe)s,
                %(role)s,
                %(ready_created_at)s,
                %(close)s,
                %(prev_high)s,
                %(status)s,
                'RADAR',
                %(delivery_status)s,
                %(delivery_reason)s,
                %(dry_run)s,
                %(telegram_result_status)s,
                %(telegram_result_reason)s,
                FALSE,
                FALSE,
                FALSE
            )
            ON CONFLICT (ready_row_id) DO NOTHING
            """,
            {
                "ready_row_id": event.row_id,
                "snapshot_id": event.snapshot_id,
                "symbol": event.symbol,
                "asset_class": event.asset_class,
                "timeframe": event.timeframe,
                "role": event.role,
                "ready_created_at": event.created_at,
                "close": event.close,
                "prev_high": event.prev_high,
                "status": event.status,
                "delivery_status": delivery_status,
                "delivery_reason": delivery_reason,
                "dry_run": dry_run,
                "telegram_result_status": telegram_result_status,
                "telegram_result_reason": telegram_result_reason,
            },
        )


def build_message(event: ReadyEvent) -> TelegramSignalMessage:
    return TelegramSignalMessage(
        channel_type="RADAR",
        symbol=event.symbol,
        display_name=event.symbol,
        direction="BREAKOUT",
        source="MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_V1",
        strategy="MULTI_ASSET_BREAKOUT_WATCH_V2",
        timeframe=event.timeframe,
        confidence=0.70,
        entry=float(event.close) if event.close is not None else None,
        stop=None,
        take=None,
        risk_comment="watch-alert only; execution=disabled; real_trading=disabled",
        reason=(
            f"{event.asset_class} {event.role}: BREAKOUT_READY; "
            f"close={event.close}; prev_high={event.prev_high}; ready_row_id={event.row_id}"
        ),
    )


def main() -> int:
    print("=== MULTI ASSET BREAKOUT READY EVENT DELIVERY V1 ===")
    print("mode=delivery_guarded")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")

    dry_run = os.getenv("MULTI_ASSET_READY_EVENT_DRY_RUN", "1") != "0"
    limit = int(os.getenv("MULTI_ASSET_READY_EVENT_LIMIT", "20"))
    print(f"delivery_dry_run={int(dry_run)}")
    print(f"limit={limit}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    delivered = 0
    skipped = 0

    with psycopg.connect(database_url) as conn:
        ensure_schema(conn)
        events = fetch_undelivered_ready_events(conn, limit)

        print()
        print("MULTI_ASSET_BREAKOUT_READY_EVENT_ROWS")
        if not events:
            print("MULTI_ASSET_BREAKOUT_READY_EVENT_ROW status=NO_UNDELIVERED_READY_EVENTS")

        for event in events:
            print(
                "MULTI_ASSET_BREAKOUT_READY_EVENT_ROW "
                f"ready_row_id={event.row_id} symbol={event.symbol} timeframe={event.timeframe} "
                f"role={event.role} close={event.close} prev_high={event.prev_high} status={event.status}"
            )

            if dry_run:
                save_delivery(
                    conn,
                    event,
                    delivery_status="DRY_RUN_RECORDED",
                    delivery_reason="dry_run_no_telegram_send",
                    dry_run=True,
                    telegram_result_status="dry_run",
                    telegram_result_reason="dry_run_no_telegram_send",
                )
                print(
                    "MULTI_ASSET_BREAKOUT_READY_EVENT_DRY_RUN "
                    f"ready_row_id={event.row_id} symbol={event.symbol} channel_type=RADAR"
                )
                skipped += 1
                continue

            result = TelegramSignalDispatcher().dispatch(build_message(event))
            save_delivery(
                conn,
                event,
                delivery_status="SENT" if result.status == "sent" else "SEND_FAILED",
                delivery_reason=result.reason,
                dry_run=False,
                telegram_result_status=result.status,
                telegram_result_reason=result.reason,
            )
            print(
                "MULTI_ASSET_BREAKOUT_READY_EVENT_SEND_RESULT "
                f"ready_row_id={event.row_id} symbol={event.symbol} "
                f"status={result.status} channel_type={result.channel_type} "
                f"target_env={result.target_env} reason={result.reason}"
            )
            delivered += int(result.status == "sent")

        conn.commit()

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT count(*)::int
                FROM analytics_multi_asset_breakout_row_v1
                WHERE status LIKE %(ready_pattern)s
                """,
                {"ready_pattern": "%BREAKOUT_READY%"},
            )
            ready_total = int(cur.fetchone()["count"] or 0)

            cur.execute(
                """
                SELECT count(*)::int
                FROM analytics_multi_asset_breakout_ready_delivery_v1
                """
            )
            delivery_total = int(cur.fetchone()["count"] or 0)

            cur.execute(
                """
                SELECT count(*)::int
                FROM analytics_multi_asset_breakout_ready_delivery_v1
                WHERE dry_run IS TRUE
                """
            )
            dry_run_total = int(cur.fetchone()["count"] or 0)

    print()
    print("MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_SUMMARY")
    print(f"ready_total={ready_total}")
    print(f"undelivered_before={len(events)}")
    print(f"delivery_total={delivery_total}")
    print(f"dry_run_total={dry_run_total}")
    print(f"delivered={delivered}")
    print(f"skipped={skipped}")
    print(f"delivery_dry_run={int(dry_run)}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not events:
        print("VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_NO_NEW_READY")
    elif dry_run:
        print("VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_DRY_RUN_RECORDED")
    elif delivered > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_SENT")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_REVIEW_REQUIRED")

    print("MULTI_ASSET_BREAKOUT_READY_EVENT_DELIVERY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
