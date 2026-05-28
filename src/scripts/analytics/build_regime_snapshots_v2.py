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


def load_market_view_rows(
    conn: psycopg.Connection,
    trade_date: date,
    output_symbol: str,
    timeframe: str,
    source_view: str,
    limit: int,
) -> list[dict[str, Any]]:
    # Русский комментарий:
    # Для rolling continuous режима нет feature_snapshots по синтетическому символу.
    # Поэтому строим минимальный regime-профиль прямо из OHLC rolling-view.
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"""
        WITH base AS (
            SELECT
                ts,
                %s::text AS symbol,
                COALESCE(NULLIF(timeframe, ''), %s) AS timeframe,
                open,
                high,
                low,
                close,
                volume,
                lag(close, 12) OVER (ORDER BY ts) AS close_12,
                avg(high - low) OVER (
                    ORDER BY ts
                    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                ) AS avg_range_20,
                avg(high - low) OVER (
                    ORDER BY ts
                    ROWS BETWEEN 99 PRECEDING AND CURRENT ROW
                ) AS avg_range_100,
                EXTRACT(HOUR FROM (ts AT TIME ZONE 'Europe/Moscow'))::int AS hour_msk
            FROM {source_view}
            WHERE timeframe = %s
              AND (ts AT TIME ZONE 'Europe/Moscow')::date = %s
            ORDER BY ts
        )
        SELECT
            ts,
            symbol,
            timeframe,
            jsonb_build_object(
                'source', 'market_bars_rolling_view',
                'quality', 'PARTIAL',
                'open', open,
                'high', high,
                'low', low,
                'close', close,
                'volume', volume,
                'atr_proxy', COALESCE(avg_range_20, 0),
                'trend_state',
                    CASE
                        WHEN close_12 IS NULL THEN 'unknown'
                        WHEN close > close_12 THEN 'up'
                        WHEN close < close_12 THEN 'down'
                        ELSE 'flat'
                    END,
                'volatility_state',
                    CASE
                        WHEN avg_range_20 IS NULL OR avg_range_100 IS NULL OR avg_range_100 = 0 THEN 'unknown'
                        WHEN avg_range_20 >= avg_range_100 * 1.20 THEN 'high'
                        WHEN avg_range_20 <= avg_range_100 * 0.80 THEN 'low'
                        ELSE 'normal'
                    END,
                'range_state',
                    CASE
                        WHEN avg_range_20 IS NULL OR avg_range_100 IS NULL OR avg_range_100 = 0 THEN 'unknown'
                        WHEN avg_range_20 <= avg_range_100 * 0.80 THEN 'compression'
                        ELSE 'normal'
                    END
            ) AS payload,
            hour_msk
        FROM base
        ORDER BY ts DESC
        LIMIT %s
        """, (output_symbol, timeframe, timeframe, trade_date, limit))
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
    # Русский комментарий:
    # Semantic enrichment строится на фактической схеме feature_snapshots
    # или на синтетических признаках rolling-view:
    # volatility_state, trend_state, range_state, atr_proxy.

    volatility = _text(payload, "volatility_state", default="unknown")
    trend = _text(payload, "trend_state", default="unknown")
    range_state = _text(payload, "range_state", default="unknown")
    quality = _text(payload, "quality", default="PARTIAL")

    atr_proxy = _float(payload, "atr_proxy", default=0.0)
    fx_stress = _float(payload, "fx_stress_score", default=0.0)
    commodity_score = _float(payload, "commodity_score", default=0.0)

    if volatility == "low" and trend == "flat":
        compression = "compression"
    elif volatility == "high" and trend in {"up", "down"}:
        compression = "expansion"
    else:
        compression = "normal"

    if compression == "compression":
        regime = "compression"
    elif compression == "expansion" and trend == "up":
        regime = "trend_up_expansion"
    elif compression == "expansion" and trend == "down":
        regime = "trend_down_expansion"
    elif trend == "up":
        regime = "trend_up"
    elif trend == "down":
        regime = "trend_down"
    elif range_state not in {"unknown", ""}:
        regime = f"range_{range_state}"
    else:
        regime = "range_unknown"

    confidence = 0.35

    if quality == "FULL":
        confidence += 0.25
    elif quality == "PARTIAL":
        confidence += 0.10

    if volatility != "unknown":
        confidence += 0.15

    if trend != "unknown":
        confidence += 0.15

    if atr_proxy > 0:
        confidence += 0.05

    if abs(fx_stress) > 0 or abs(commodity_score) > 0:
        confidence += 0.05

    confidence = max(0.0, min(1.0, confidence))

    return regime, volatility, trend, compression, confidence


def build_snapshots(
    conn: psycopg.Connection,
    trade_date: date,
    symbol: str | None,
    limit: int,
    timeframe: str = "M5",
    source_view: str | None = None,
) -> list[RegimeSnapshot]:
    if source_view:
        if not symbol:
            raise ValueError("--symbol is required when --source-view is used")
        rows = load_market_view_rows(
            conn=conn,
            trade_date=trade_date,
            output_symbol=symbol,
            timeframe=timeframe,
            source_view=source_view,
            limit=limit,
        )
        source = f"market_view:{source_view}"
    else:
        rows = load_feature_rows(conn, trade_date=trade_date, symbol=symbol, limit=limit)
        source = "feature_snapshots"

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
                source=source,
                payload=payload,
            )
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--source-view", default=None)
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
            timeframe=args.timeframe,
            source_view=args.source_view,
        )

    if args.save:
        for item in snapshots:
            repo.save(item)

    print(
        f"REGIME_SNAPSHOTS_V2_OK date={trade_date} symbol={args.symbol or '*'} "
        f"source_view={args.source_view or '-'} saved={len(snapshots)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
