# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import psycopg2

from finam_core.data.moex_client import MoexClient
from finam_core.data.market_radar import MarketRadar
from finam_core.storage.dynamic_watchlist_repository import DynamicWatchlistRepository
from finam_core.storage.postgres_logger import PostgresLogger
from finam_core.notifications.notification_router import NotificationRouter
from finam_core.data.radar_persistence_repository import RadarPersistenceRepository


def print_bucket(title: str, rows) -> None:
    print(title)
    for i, c in enumerate(rows, start=1):
        print(
            f"{i:02d}. {c.symbol:12s} {c.name:24s} "
            f"chg={c.change_pct:7.2f}% rs={c.relative_strength:7.2f}% "
            f"value={c.value_today:,.0f} trades={c.num_trades} "
            f"score={c.score:.4f} status={c.status}"
        )


def candidate_to_dict(c) -> dict:
    return {
        "symbol": c.symbol,
        "name": c.name,
        "direction": c.direction,
        "change_pct": c.change_pct,
        "relative_strength": c.relative_strength,
        "value_today": c.value_today,
        "volume_today": c.volume_today,
        "num_trades": c.num_trades,
        "score": c.score,
        "status": c.status,
        "portfolio_status": "UNKNOWN",
        "portfolio_action": "WATCH_FOR_ENTRY",
    }


def save_radar_results(rows: list[dict]) -> int:
    if not rows:
        return 0

    dsn = os.getenv("DATABASE_URL", "dbname=finam user=finam password=finam host=localhost")

    sql = """
    INSERT INTO market_radar_results (
        symbol, name, direction, change_pct, relative_strength,
        value_today, volume_today, num_trades, score, status, source
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'moex_iss')
    """

    payload = [
        (
            r["symbol"],
            r["name"],
            r["direction"],
            r["change_pct"],
            r["relative_strength"],
            r["value_today"],
            r["volume_today"],
            r["num_trades"],
            r["score"],
            r["status"],
        )
        for r in rows
    ]

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, payload)

    return len(payload)


def send_top5_telegram(rows: list[dict]) -> None:
    """Русский комментарий: отправляет отдельное Telegram-сообщение по каждому инструменту."""

    if not rows:
        print("WATCHLIST_TELEGRAM_SKIP reason=empty")
        return

    from finam_core.notifications.telegram_notifier import TelegramNotifier

    notifier = TelegramNotifier()

    sent = 0

    for r in rows[:10]:
        symbol = str(r.get("symbol") or "")
        name = str(r.get("short_name") or r.get("name") or "")
        change_pct = float(r.get("change_pct") or r.get("chg") or 0.0)
        rel_strength = float(r.get("relative_strength") or r.get("rs") or 0.0)
        score = float(r.get("score") or 0.0)
        status = str(r.get("status") or "КАНДИДАТ")

        last_price = float(
            r.get("last_price")
            or r.get("last")
            or r.get("price")
            or r.get("close")
            or 0.0
        )

        # Русский комментарий: базовая торговая гипотеза для radar.
        if change_pct >= 0:
            direction = "ЛОНГ / наблюдение за продолжением импульса"
            entry = last_price
            stop = last_price * 0.985 if last_price > 0 else 0.0
            take = last_price * 1.030 if last_price > 0 else 0.0
        else:
            direction = "ОТСКОК / наблюдение за разворотом после снижения"
            entry = last_price
            stop = last_price * 0.970 if last_price > 0 else 0.0
            take = last_price * 1.025 if last_price > 0 else 0.0

        if last_price <= 0:
            entry_text = "нет цены — вход не рассчитывается"
            stop_text = "нет цены"
            take_text = "нет цены"
        else:
            entry_text = f"{entry:.4f}"
            stop_text = f"{stop:.4f}"
            take_text = f"{take:.4f}"

        text = (
            "📌 <b>Торговый кандидат TOP-10</b>\n\n"
            f"Инструмент: <b>{symbol}</b>\n"
            f"Название: {name}\n"
            f"Статус: {status}\n\n"
            f"Направление: {direction}\n"
            f"Точка входа: <b>{entry_text}</b>\n"
            f"Стоп-лосс: <b>{stop_text}</b>\n"
            f"Тейк-профит: <b>{take_text}</b>\n\n"
            f"Изменение: {change_pct:.2f}%\n"
            f"Относительная сила: {rel_strength:.2f}%\n"
            f"Оценка сигнала: {score:.4f}\n\n"
            "Решение: не рыночная заявка, а сигнал для ручной проверки."
        )

        notifier.send(text)
        sent += 1

    print(f"WATCHLIST_TELEGRAM_SENT messages={sent}")


def load_liquid_universe_symbols() -> set[str]:
    """Русский комментарий: читает liquid universe из PostgreSQL для ограничения radar scan."""
    try:
        pg = PostgresLogger()
        with pg._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select symbol
                    from moex_liquid_universe
                    where enabled = true
                    """
                )
                rows = cur.fetchall()

        symbols = {str(r[0]) for r in rows if r and r[0]}
        print(f"PIPE_LIQUID_UNIVERSE symbols={len(symbols)}")
        return symbols

    except Exception as exc:
        print(f"PIPE_LIQUID_UNIVERSE_FALLBACK reason={type(exc).__name__}:{exc}")
        return set()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-value", type=float, default=50_000_000)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--telegram-top5", action="store_true")
    parser.add_argument("--use-liquid-universe", action="store_true")
    args = parser.parse_args()

    client = MoexClient()
    imoex_change = client.get_imoex_change_pct()
    print(f"IMOEX_CHANGE={imoex_change:.2f}%")

    radar = MarketRadar(
        min_value_today=args.min_value,
        min_abs_change_pct=0.5,
        max_abs_change_pct=20.0,
    )

    liquid_symbols = load_liquid_universe_symbols() if args.use_liquid_universe else set()

    all_gainers = []
    all_losers = []
    all_anomalies = []

    for _, data in client.get_today_spot_universe().items():
        if liquid_symbols and isinstance(data, dict):
            securities = data.get("securities") or {}
            marketdata = data.get("marketdata") or {}

            sec_columns = securities.get("columns") or []
            md_columns = marketdata.get("columns") or []

            sec_symbol_idx = sec_columns.index("SECID") if "SECID" in sec_columns else None
            md_symbol_idx = md_columns.index("SECID") if "SECID" in md_columns else None

            allowed_secids = set()
            filtered_securities_data = []

            for row in securities.get("data") or []:
                if sec_symbol_idx is None or sec_symbol_idx >= len(row):
                    continue

                secid = str(row[sec_symbol_idx])
                full_symbol = f"{secid}@MISX"

                if secid in liquid_symbols or full_symbol in liquid_symbols:
                    allowed_secids.add(secid)
                    filtered_securities_data.append(row)

            filtered_marketdata_data = []
            for row in marketdata.get("data") or []:
                if md_symbol_idx is None or md_symbol_idx >= len(row):
                    continue

                secid = str(row[md_symbol_idx])
                if secid in allowed_secids:
                    filtered_marketdata_data.append(row)

            data = dict(data)
            data["securities"] = dict(securities)
            data["marketdata"] = dict(marketdata)
            data["securities"]["data"] = filtered_securities_data
            data["marketdata"]["data"] = filtered_marketdata_data

            print(
                f"PIPE_LIQUID_UNIVERSE_FILTERED "
                f"securities={len(filtered_securities_data)} "
                f"marketdata={len(filtered_marketdata_data)}"
            )

        result = radar.build(data, top_n=100, imoex_change_pct=imoex_change)
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

    clean_rows = [candidate_to_dict(c) for c in gainers + losers]

    anomaly_rows = []
    for c in anomalies:
        row = candidate_to_dict(c)
        row["strategy"] = "MANUAL_REVIEW"
        row["status"] = "ANOMALY_REVIEW"
        row["reason"] = "anomaly_guard_manual_review_only"
        anomaly_rows.append(row)

    all_rows = clean_rows + anomaly_rows

    persistence = RadarPersistenceRepository().load_persistence(hours=4)
    for row in clean_rows:
        pstate = persistence.get(row["symbol"], {})
        row["appearances"] = pstate.get("appearances", 0)
        row["score_delta"] = pstate.get("score_delta", 0.0)
        row["persistence_state"] = pstate.get("persistence_state", "ONE_SHOT")

    if args.no_db:
        print("MARKET_RADAR_DB_SAVE_SKIPPED")
    else:
        saved = save_radar_results(all_rows)
        watchlist_saved = DynamicWatchlistRepository().replace_watchlist(clean_rows[: args.top_n])
        print(f"MARKET_RADAR_DB_SAVED rows={saved}")
        print(f"DYNAMIC_WATCHLIST_UPDATED rows={watchlist_saved}")

    if args.send_telegram or args.telegram_top5:
        send_top5_telegram(clean_rows)

    print("MARKET_RADAR_CLEAN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
