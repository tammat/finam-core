#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import Counter, defaultdict

import psycopg2


SYMBOLS = ["BRN6@RTSX", "NGN6@RTSX", "USDRUBF@RTSX", "BTCUSD", "ETHUSD"]


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def regime(compression: bool, expansion: bool) -> str:
    if expansion:
        return "EXPANSION"
    if compression:
        return "COMPRESSION"
    return "MIXED"


def main() -> None:
    print("=== CROSS MARKET REGIME MATRIX V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("timeframe=M5")
    print()

    sql = """
        select
            symbol,
            timeframe,
            date_trunc('minute', ts) as bucket_ts,
            compression_flag,
            expansion_flag,
            atr_pct_14,
            momentum_20
        from research_feature_store
        where symbol = any(%s)
          and timeframe = 'M5'
        order by bucket_ts, symbol;
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, (SYMBOLS,))
            rows = cur.fetchall()

    if not rows:
        print("MATRIX_ROW none")
        print("VERDICT=NO_FEATURE_DATA")
        return

    buckets: dict[object, dict[str, str]] = defaultdict(dict)

    for symbol, timeframe, bucket_ts, compression_flag, expansion_flag, atr_pct_14, momentum_20 in rows:
        buckets[bucket_ts][symbol] = regime(bool(compression_flag), bool(expansion_flag))

    complete_buckets = {
        ts: state
        for ts, state in buckets.items()
        if all(symbol in state for symbol in SYMBOLS)
    }

    print(f"TOTAL_BUCKETS={len(buckets)}")
    print(f"COMPLETE_BUCKETS={len(complete_buckets)}")
    print()

    if not complete_buckets:
        print("VERDICT=NO_COMPLETE_BUCKETS")
        return

    combo_counter = Counter()
    pair_counter = Counter()

    for ts, state in complete_buckets.items():
        combo = "|".join(f"{s}:{state[s]}" for s in SYMBOLS)
        combo_counter[combo] += 1

        for i, left in enumerate(SYMBOLS):
            for right in SYMBOLS[i + 1:]:
                pair_key = (
                    left,
                    state[left],
                    right,
                    state[right],
                )
                pair_counter[pair_key] += 1

    print("TOP_COMBINATIONS")
    for combo, count in combo_counter.most_common(10):
        rate = count / len(complete_buckets)
        print(f"COMBO_ROW count={count} rate={rate:.4f} combo={combo}")

    print()
    print("PAIR_MATRIX")
    for (left, left_regime, right, right_regime), count in pair_counter.most_common(30):
        rate = count / len(complete_buckets)
        print(
            f"PAIR_ROW left={left} left_regime={left_regime} "
            f"right={right} right_regime={right_regime} "
            f"count={count} rate={rate:.4f}"
        )

    print()
    print("FOCUS_PATTERNS")

    patterns = {
        "ENERGY_USD_ALL_COMPRESSION": 0,
        "BTC_ETH_BOTH_EXPANSION": 0,
        "ENERGY_COMPRESSION_CRYPTO_EXPANSION": 0,
        "NG_EXPANSION_USD_COMPRESSION": 0,
        "BR_EXPANSION_BTC_COMPRESSION": 0,
    }

    for state in complete_buckets.values():
        if (
            state["BRN6@RTSX"] == "COMPRESSION"
            and state["NGN6@RTSX"] == "COMPRESSION"
            and state["USDRUBF@RTSX"] == "COMPRESSION"
        ):
            patterns["ENERGY_USD_ALL_COMPRESSION"] += 1

        if state["BTCUSD"] == "EXPANSION" and state["ETHUSD"] == "EXPANSION":
            patterns["BTC_ETH_BOTH_EXPANSION"] += 1

        if (
            state["BRN6@RTSX"] == "COMPRESSION"
            and state["NGN6@RTSX"] == "COMPRESSION"
            and state["BTCUSD"] == "EXPANSION"
            and state["ETHUSD"] == "EXPANSION"
        ):
            patterns["ENERGY_COMPRESSION_CRYPTO_EXPANSION"] += 1

        if state["NGN6@RTSX"] == "EXPANSION" and state["USDRUBF@RTSX"] == "COMPRESSION":
            patterns["NG_EXPANSION_USD_COMPRESSION"] += 1

        if state["BRN6@RTSX"] == "EXPANSION" and state["BTCUSD"] == "COMPRESSION":
            patterns["BR_EXPANSION_BTC_COMPRESSION"] += 1

    for name, count in patterns.items():
        rate = count / len(complete_buckets)
        print(f"PATTERN_ROW pattern={name} count={count} rate={rate:.4f}")

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
