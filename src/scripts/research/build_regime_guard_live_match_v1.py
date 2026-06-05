#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


SYMBOLS = [
    "BRN6@RTSX",
    "NGN6@RTSX",
    "USDRUBF@RTSX",
    "BTCUSD",
    "ETHUSD",
]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def classify(compression, expansion):
    if expansion:
        return "EXPANSION"
    if compression:
        return "COMPRESSION"
    return "MIXED"


def main():
    print("=== REGIME GUARD LIVE MATCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("advisory_only=1")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                select distinct on (symbol)
                    symbol,
                    ts,
                    compression_flag,
                    expansion_flag
                from research_feature_store
                where timeframe='M5'
                  and symbol = any(%s)
                order by symbol, ts desc
                """,
                (SYMBOLS,),
            )
            feature_rows = cur.fetchall()

            cur.execute(
                """
                select
                    scope,
                    regime_key,
                    classification,
                    reason,
                    trades,
                    net_pnl,
                    expectancy,
                    profit_factor
                from research_regime_guard_candidates
                where source='regime_guard_candidate_v1'
                """
            )
            candidate_rows = cur.fetchall()

    snapshot = {}
    for symbol, ts, compression, expansion in feature_rows:
        snapshot[symbol] = classify(bool(compression), bool(expansion))
        print(f"SNAPSHOT_ROW symbol={symbol} regime={snapshot[symbol]} ts={ts}")

    br = snapshot.get("BRN6@RTSX", "NA")
    ng = snapshot.get("NGN6@RTSX", "NA")
    usd = snapshot.get("USDRUBF@RTSX", "NA")
    btc = snapshot.get("BTCUSD", "NA")
    eth = snapshot.get("ETHUSD", "NA")

    energy_key = f"BR={br}|NG={ng}|USD={usd}"
    crypto_key = f"BTC={btc}|ETH={eth}"
    full_key = f"{energy_key}|{crypto_key}"

    candidates = {
        (scope, regime_key): {
            "classification": classification,
            "reason": reason,
            "trades": int(trades or 0),
            "net_pnl": float(net_pnl or 0),
            "expectancy": float(expectancy or 0),
            "profit_factor": None if profit_factor is None else float(profit_factor),
        }
        for (
            scope,
            regime_key,
            classification,
            reason,
            trades,
            net_pnl,
            expectancy,
            profit_factor,
        ) in candidate_rows
    }

    print()
    print(f"ENERGY_USD_KEY={energy_key}")
    print(f"CRYPTO_KEY={crypto_key}")
    print(f"FULL_KEY={full_key}")
    print()

    checks = [
        ("ENERGY_USD", energy_key),
        ("CRYPTO", crypto_key),
        ("FULL", full_key),
    ]

    matched = 0
    would_block_total = 0

    for scope, key in checks:
        item = candidates.get((scope, key))
        if item is None:
            print(
                f"MATCH_ROW scope={scope} key={key} "
                "matched=0 classification=NO_MATCH would_block=0 actual_block=0 "
                "advisory_only=1 reason=no_candidate"
            )
            continue

        matched += 1
        classification = item["classification"]
        would_block = 1 if classification == "BLOCK_CANDIDATE" else 0
        would_block_total += would_block

        pf = item["profit_factor"]
        pf_text = "None" if pf is None else f"{pf:.8f}"

        print(
            f"MATCH_ROW scope={scope} key={key} matched=1 "
            f"classification={classification} reason={item['reason']} "
            f"trades={item['trades']} net_pnl={item['net_pnl']:.8f} "
            f"expectancy={item['expectancy']:.8f} "
            f"profit_factor={pf_text} "
            f"would_block={would_block} actual_block=0 advisory_only=1"
        )

    print()
    print(
        "PIPE_REGIME_GUARD_ADVISORY "
        f"energy_key={energy_key} crypto_key={crypto_key} full_key={full_key} "
        f"matched={matched} would_block={would_block_total} actual_block=0 advisory_only=1"
    )

    print("VERDICT=OK")


if __name__ == "__main__":
    main()
