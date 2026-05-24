from __future__ import annotations

import argparse
import os

import psycopg

from finam_core.features.market_feature_snapshot import (
    calculate_snapshot_quality,
    classify_range,
    classify_session_state,
    classify_trend,
    classify_volatility,
    normalize_root_symbol,
)


def load_latest_intermarket(conn) -> dict[str, object]:
    """Русский комментарий: берем последний межрыночный режим как контекст snapshot."""
    sql = """
    SELECT
        risk_mode,
        commodity_mode,
        fx_stress_score,
        commodity_score
    FROM intermarket_regime_snapshots
    ORDER BY ts DESC
    LIMIT 1;
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone()

    if row is None:
        return {
            "risk_mode": "unknown",
            "commodity_mode": "unknown",
            "fx_stress_score": 0.0,
            "commodity_score": 0.0,
        }

    return {
        "risk_mode": str(row[0]),
        "commodity_mode": str(row[1]),
        "fx_stress_score": float(row[2]),
        "commodity_score": float(row[3]),
    }


def build_for_symbol(conn, *, symbol: str, timeframe: str, limit: int, lookback_n: int) -> int:
    """Русский комментарий: строит feature snapshots по последним market_bars."""
    intermarket = load_latest_intermarket(conn)

    sql = """
    WITH ordered AS (
        SELECT
            symbol,
            timeframe,
            ts,
            close::float AS close,
            LAG(close::float, 1) OVER (PARTITION BY symbol, timeframe ORDER BY ts) AS prev_close,
            LAG(close::float, %(lookback_n)s) OVER (PARTITION BY symbol, timeframe ORDER BY ts) AS n_close,
            high::float AS high,
            low::float AS low
        FROM market_bars
        WHERE symbol = %(symbol)s
          AND timeframe = %(timeframe)s
          AND close IS NOT NULL
        ORDER BY ts DESC
        LIMIT %(limit)s
    )
    SELECT
        symbol,
        timeframe,
        ts,
        close,
        prev_close,
        n_close,
        high,
        low
    FROM ordered
    ORDER BY ts ASC;
    """

    insert_sql = """
    INSERT INTO feature_snapshots (
        symbol,
        root_symbol,
        timeframe,
        ts,
        close,
        return_1,
        return_n,
        atr_proxy,
        volatility_state,
        trend_state,
        range_state,
        session_state,
        intermarket_risk_mode,
        intermarket_commodity_mode,
        fx_stress_score,
        commodity_score,
        quality,
        reason
    )
    VALUES (
        %(symbol)s,
        %(root_symbol)s,
        %(timeframe)s,
        %(ts)s,
        %(close)s,
        %(return_1)s,
        %(return_n)s,
        %(atr_proxy)s,
        %(volatility_state)s,
        %(trend_state)s,
        %(range_state)s,
        %(session_state)s,
        %(intermarket_risk_mode)s,
        %(intermarket_commodity_mode)s,
        %(fx_stress_score)s,
        %(commodity_score)s,
        %(quality)s,
        %(reason)s
    )
    ON CONFLICT (symbol, timeframe, ts) DO UPDATE
    SET
        close = EXCLUDED.close,
        return_1 = EXCLUDED.return_1,
        return_n = EXCLUDED.return_n,
        atr_proxy = EXCLUDED.atr_proxy,
        volatility_state = EXCLUDED.volatility_state,
        trend_state = EXCLUDED.trend_state,
        range_state = EXCLUDED.range_state,
        session_state = EXCLUDED.session_state,
        intermarket_risk_mode = EXCLUDED.intermarket_risk_mode,
        intermarket_commodity_mode = EXCLUDED.intermarket_commodity_mode,
        fx_stress_score = EXCLUDED.fx_stress_score,
        commodity_score = EXCLUDED.commodity_score,
        quality = EXCLUDED.quality,
        reason = EXCLUDED.reason,
        created_at = now();
    """

    saved = 0

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "lookback_n": lookback_n,
            },
        )
        rows = cur.fetchall()

        for row in rows:
            (
                row_symbol,
                row_timeframe,
                ts,
                close,
                prev_close,
                n_close,
                high,
                low,
            ) = row

            if prev_close and prev_close != 0:
                return_1 = (float(close) - float(prev_close)) / float(prev_close)
            else:
                return_1 = 0.0

            if n_close and n_close != 0:
                return_n = (float(close) - float(n_close)) / float(n_close)
            else:
                return_n = 0.0

            if close and close != 0 and high is not None and low is not None:
                atr_proxy = abs(float(high) - float(low)) / float(close)
            else:
                atr_proxy = 0.0

            volatility_state = classify_volatility(atr_proxy)
            trend_state = classify_trend(return_n)
            range_state = classify_range(return_1, atr_proxy)
            session_state = classify_session_state(int(ts.hour))

            quality, reason = calculate_snapshot_quality(
                intermarket_risk_mode=str(intermarket["risk_mode"]),
                intermarket_commodity_mode=str(intermarket["commodity_mode"]),
                atr_proxy=atr_proxy,
            )

            cur.execute(
                insert_sql,
                {
                    "symbol": row_symbol,
                    "root_symbol": normalize_root_symbol(str(row_symbol)),
                    "timeframe": row_timeframe,
                    "ts": ts,
                    "close": close,
                    "return_1": return_1,
                    "return_n": return_n,
                    "atr_proxy": atr_proxy,
                    "volatility_state": volatility_state,
                    "trend_state": trend_state,
                    "range_state": range_state,
                    "session_state": session_state,
                    "intermarket_risk_mode": intermarket["risk_mode"],
                    "intermarket_commodity_mode": intermarket["commodity_mode"],
                    "fx_stress_score": intermarket["fx_stress_score"],
                    "commodity_score": intermarket["commodity_score"],
                    "quality": quality,
                    "reason": reason,
                },
            )
            saved += 1

    return saved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--lookback-n", type=int, default=12)
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    total = 0

    with psycopg.connect(database_url) as conn:
        for symbol in symbols:
            saved = build_for_symbol(
                conn,
                symbol=symbol,
                timeframe=args.timeframe,
                limit=args.limit,
                lookback_n=args.lookback_n,
            )
            total += saved
            print(
                "FEATURE_SNAPSHOTS_SYMBOL_OK "
                f"symbol={symbol} timeframe={args.timeframe} saved={saved}",
                flush=True,
            )

        conn.commit()

    print(f"FEATURE_SNAPSHOTS_BUILD_OK symbols={len(symbols)} saved={total}", flush=True)


if __name__ == "__main__":
    main()
