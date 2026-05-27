from __future__ import annotations

import argparse
import os
from datetime import date
from typing import Any

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.regime_snapshot_repository import (
    RegimeSnapshot,
    RegimeSnapshotRepository,
)
from finam_core.analytics.statistics_repository import build_psycopg_url


def _session_from_ts_msk(hour: int) -> str:
    if 7 <= hour < 10:
        return "morning"
    if 10 <= hour < 14:
        return "main_1"
    if 14 <= hour < 19:
        return "main_2"
    if 19 <= hour <= 23:
        return "evening"
    return "overnight"


def _text(payload: dict[str, Any], *keys: str, default: str = "unknown") -> str:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def _float(payload: dict[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except Exception:
                continue
    return default


def load_feature_rows(conn: psycopg.Connection, trade_date: date, symbol: str | None, limit: int) -> list[dict[str, Any]]:
    where = ["(ts AT TIME ZONE 'Europe/Moscow')::date = %s"]
    params: list[Any] = [trade_date]

    if symbol:
        where.append("symbol = %s")
        params.append(symbol)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"""
        SELECT
            ts,
            symbol,
            COALESCE(NULLIF(timeframe, ''), 'M5') AS timeframe,
            to_jsonb(f.*) AS payload,
            EXTRACT(HOUR FROM (ts AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk
        FROM feature_snapshots f
        WHERE {' AND '.join(where)}
        ORDER BY ts DESC
        LIMIT %s
        """, (*params, limit))
        return [dict(r) for r in cur.fetchall()]


def load_intermarket_state(conn: psycopg.Connection) -> str:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""
        SELECT to_jsonb(t.*) AS payload
        FROM intermarket_regime_snapshots t
        ORDER BY ctid DESC
        LIMIT 1
        """)
        row = cur.fetchone()
        if not row or not isinstance(row["payload"], dict):
            return "unknown"

        payload = row["payload"]
        risk_mode = _text(payload, "risk_mode", default="")
        commodity_mode = _text(payload, "commodity_mode", default="")
        if risk_mode or commodity_mode:
            return f"{risk_mode}:{commodity_mode}".strip(":")
        return "unknown"


def classify(payload: dict[str, Any]) -> tuple[str, str, str, str, float]:
    regime = _text(payload, "regime", "market_regime", "trend_regime", default="unknown")
    volatility = _text(payload, "volatility_regime", "atr_state", "volatility", default="unknown")
    trend = _text(payload, "trend_regime", "trend", "trend_state", default="unknown")
    compression = _text(payload, "compression_state", "compression", "squeeze_state", default="unknown")
    confidence = _float(payload, "confidence", "regime_confidence", "score", default=0.0)

    return regime, volatility, trend, compression, confidence


def build_snapshots(
    conn: psycopg.Connection,
    trade_date: date,
    symbol: str | None,
    limit: int,
) -> list[RegimeSnapshot]:
    rows = load_feature_rows(conn, trade_date=trade_date, symbol=symbol, limit=limit)
    intermarket_state = load_intermarket_state(conn)
    result: list[RegimeSnapshot] = []

    for row in rows:
        payload = row["payload"] if isinstance(row["payload"], dict) else {}
        regime, volatility, trend, compression, confidence = classify(payload)

        result.append(
            RegimeSnapshot(
                ts=row["ts"],
                symbol=str(row["symbol"]),
                timeframe=str(row["timeframe"]),
                regime=regime,
                volatility_regime=volatility,
                trend_regime=trend,
                compression_state=compression,
                intermarket_state=intermarket_state,
                session_type=_session_from_ts_msk(int(row["hour_msk"] or 0)),
                confidence=confidence,
                source="feature_snapshots",
                payload=payload,
            )
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    trade_date = date.fromisoformat(args.date)
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()
    repo = RegimeSnapshotRepository(database_url)

    if args.migrate:
        repo.migrate()

    with psycopg.connect(database_url) as conn:
        snapshots = build_snapshots(
            conn=conn,
            trade_date=trade_date,
            symbol=args.symbol,
            limit=args.limit,
        )

    if args.save:
        for item in snapshots:
            repo.save(item)

    print(
        f"REGIME_SNAPSHOTS_V2_OK date={trade_date} symbol={args.symbol or '*'} saved={len(snapshots)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
