#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict

import psycopg2


SYMBOLS = ["BRN6@RTSX", "NGN6@RTSX", "USDRUBF@RTSX", "BTCUSD", "ETHUSD"]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def metrics(rows):
    trades = len(rows)
    pnl = sum(float(r["net_pnl"] or 0) for r in rows)
    wins = sum(1 for r in rows if float(r["net_pnl"] or 0) > 0)
    losses = sum(1 for r in rows if float(r["net_pnl"] or 0) < 0)
    gp = sum(float(r["net_pnl"] or 0) for r in rows if float(r["net_pnl"] or 0) > 0)
    gl = abs(sum(float(r["net_pnl"] or 0) for r in rows if float(r["net_pnl"] or 0) < 0))
    pf = None if gl == 0 else gp / gl
    return trades, pnl, wins, losses, (wins / trades if trades else 0), (pnl / trades if trades else 0), pf


def print_metric(prefix, key, rows):
    trades, pnl, wins, losses, winrate, expectancy, pf = metrics(rows)
    print(
        f"{prefix} key={key} trades={trades} wins={wins} losses={losses} "
        f"winrate={winrate:.4f} net_pnl={pnl:.8f} expectancy={expectancy:.8f} "
        f"profit_factor={'None' if pf is None else f'{pf:.8f}'}"
    )


def main() -> None:
    print("=== CROSS MARKET REGIME SIGNAL QUALITY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("timeframe=M5")
    print()

    sql = """
        with trades_base as (
            select
                id,
                symbol as trade_symbol,
                strategy,
                side,
                timeframe,
                net_pnl,
                coalesce(
                    (payload->'entry_payload'->>'ts')::timestamptz,
                    (payload->>'entry_ts')::timestamptz,
                    opened_at,
                    created_at
                ) as entry_ts
            from closed_trades
            where source = 'closed_trade_engine_v1_1'
              and trade_source = 'paper'
        ),
        feature_base as (
            select
                symbol,
                ts,
                case
                    when expansion_flag then 'EXPANSION'
                    when compression_flag then 'COMPRESSION'
                    else 'MIXED'
                end as regime
            from research_feature_store
            where timeframe = 'M5'
              and symbol = any(%s)
        )
        select
            t.id,
            t.trade_symbol,
            t.strategy,
            t.side,
            t.timeframe,
            t.net_pnl,
            date_trunc('minute', t.entry_ts) as entry_bucket,
            br.regime as br_regime,
            ng.regime as ng_regime,
            usd.regime as usd_regime,
            btc.regime as btc_regime,
            eth.regime as eth_regime
        from trades_base t
        left join feature_base br
          on br.symbol='BRN6@RTSX'
         and br.ts = date_trunc('minute', t.entry_ts)
        left join feature_base ng
          on ng.symbol='NGN6@RTSX'
         and ng.ts = date_trunc('minute', t.entry_ts)
        left join feature_base usd
          on usd.symbol='USDRUBF@RTSX'
         and usd.ts = date_trunc('minute', t.entry_ts)
        left join feature_base btc
          on btc.symbol='BTCUSD'
         and btc.ts = date_trunc('minute', t.entry_ts)
        left join feature_base eth
          on eth.symbol='ETHUSD'
         and eth.ts = date_trunc('minute', t.entry_ts)
        order by t.entry_ts;
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, (SYMBOLS,))
            db_rows = cur.fetchall()

    rows = []
    for r in db_rows:
        (
            trade_id,
            trade_symbol,
            strategy,
            side,
            timeframe,
            net_pnl,
            entry_bucket,
            br_regime,
            ng_regime,
            usd_regime,
            btc_regime,
            eth_regime,
        ) = r

        row = {
            "trade_id": trade_id,
            "trade_symbol": trade_symbol,
            "strategy": strategy,
            "side": side,
            "timeframe": timeframe,
            "net_pnl": float(net_pnl or 0),
            "entry_bucket": entry_bucket,
            "br": br_regime or "NA",
            "ng": ng_regime or "NA",
            "usd": usd_regime or "NA",
            "btc": btc_regime or "NA",
            "eth": eth_regime or "NA",
        }
        rows.append(row)

    if not rows:
        print("TRADE_ROWS=0")
        print("VERDICT=NO_CLOSED_TRADES")
        return

    matched = [r for r in rows if not all(r[x] == "NA" for x in ("br", "ng", "usd", "btc", "eth"))]
    complete = [r for r in rows if all(r[x] != "NA" for x in ("br", "ng", "usd", "btc", "eth"))]

    print(f"TRADE_ROWS={len(rows)}")
    print(f"MATCHED_ROWS={len(matched)}")
    print(f"COMPLETE_REGIME_ROWS={len(complete)}")
    print()

    print_metric("QUALITY_ALL", "ALL_TRADES", rows)
    if matched:
        print_metric("QUALITY_MATCHED", "MATCHED_REGIME", matched)
    if complete:
        print_metric("QUALITY_COMPLETE", "COMPLETE_REGIME", complete)

    by_energy_usd = defaultdict(list)
    by_crypto = defaultdict(list)
    by_full = defaultdict(list)

    for r in matched:
        energy_key = f"BR={r['br']}|NG={r['ng']}|USD={r['usd']}"
        crypto_key = f"BTC={r['btc']}|ETH={r['eth']}"
        full_key = f"{energy_key}|{crypto_key}"

        by_energy_usd[energy_key].append(r)
        by_crypto[crypto_key].append(r)
        by_full[full_key].append(r)

    print()
    print("ENERGY_USD_QUALITY")
    for key, group in sorted(by_energy_usd.items(), key=lambda kv: metrics(kv[1])[1]):
        if len(group) >= 2:
            print_metric("ENERGY_USD_ROW", key, group)

    print()
    print("CRYPTO_QUALITY")
    for key, group in sorted(by_crypto.items(), key=lambda kv: metrics(kv[1])[1]):
        if len(group) >= 2:
            print_metric("CRYPTO_ROW", key, group)

    print()
    print("FULL_COMBO_QUALITY")
    for key, group in sorted(by_full.items(), key=lambda kv: metrics(kv[1])[1]):
        if len(group) >= 2:
            print_metric("FULL_COMBO_ROW", key, group)

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
