# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import psycopg2

from finam_core.data.moex_client import MoexClient
from finam_core.data.market_radar import MarketRadar


def print_bucket(title: str, rows) -> None:
    print(title)

    for i, c in enumerate(rows, start=1):
        print(
            f"{i:02d}. "
            f"{c.symbol:12s} "
            f"{c.name:24s} "
            f"chg={c.change_pct:7.2f}% "
            f"rs={c.relative_strength:7.2f}% "
            f"value={c.value_today:,.0f} "
            f"trades={c.num_trades} "
            f"score={c.score:.4f} "
            f"status={c.status}"
        )


def save_to_postgres(rows) -> int:
    """Русский комментарий: сохраняет результат радара в PostgreSQL."""
    if not rows:
        return 0

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        dsn = "dbname=finam user=finam password=finam host=localhost"

    sql = """
    INSERT INTO market_radar_results (
        symbol,
        name,
        direction,
        change_pct,
        relative_strength,
        value_today,
        volume_today,
        num_trades,
        score,
        status,
        source
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'moex_iss')
    """

    payload = [
        (
            c.symbol,
            c.name,
            c.direction,
            c.change_pct,
            c.relative_strength,
            c.value_today,
            c.volume_today,
            c.num_trades,
            c.score,
            c.status,
        )
        for c in rows
    ]

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, payload)

    return len(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-value", type=float, default=50_000_000)
    parser.add_argument("--no-db", action="store_true")
    args = parser.parse_args()

    client = MoexClient()
    imoex_change = client.get_imoex_change_pct()

    print(f"IMOEX_CHANGE={imoex_change:.2f}%")

    radar = MarketRadar(
        min_value_today=args.min_value,
        min_abs_change_pct=0.5,
        max_abs_change_pct=20.0,
    )

    all_gainers = []
    all_losers = []
    all_anomalies = []

    for board, data in client.get_today_spot_universe().items():
        result = radar.build(
            data,
            top_n=100,
            imoex_change_pct=imoex_change,
        )

        all_gainers.extend(result["gainers"])
        all_losers.extend(result["losers"])
        all_anomalies.extend(result["anomalies"])

    gainers = sorted(all_gainers, key=lambda x: x.score, reverse=True)[: args.top_n]
    losers = sorted(all_losers, key=lambda x: x.score, reverse=True)[: args.top_n]
    anomalies = sorted(all_anomalies, key=lambda x: abs(x.change_pct), reverse=True)[: args.top_n]

    print()
    print_bucket("=== CLEAN GAINERS ===", gainers)

    print()
    print_bucket("=== CLEAN LOSERS ===", losers)

    print()
    print_bucket("=== ANOMALIES ===", anomalies)

    rows_to_save = gainers + losers + anomalies

    if args.no_db:
        print("MARKET_RADAR_DB_SAVE_SKIPPED")
    else:
        saved = save_to_postgres(rows_to_save)
        print(f"MARKET_RADAR_DB_SAVED rows={saved}")

    print("MARKET_RADAR_CLEAN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
