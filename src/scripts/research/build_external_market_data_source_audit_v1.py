#!/usr/bin/env python3
from __future__ import annotations

SOURCES = [
    ("crypto", "BTCUSD,ETHUSD", "Binance public data", "M1,M5,M15", "high", "free", "RECOMMENDED_CRYPTO_PRIMARY", "research_only"),
    ("crypto", "BTCUSD,ETHUSD", "Binance REST klines", "M1,M5,M15", "medium", "free", "CRYPTO_INCREMENTAL_BACKFILL", "research_only"),
    ("etf", "SPY,QQQ,GLD,SLV", "Polygon/Massive", "M1,M5,M15", "high", "paid_or_limited_free", "RECOMMENDED_ETF_PRIMARY", "research_only"),
    ("etf", "SPY,QQQ,GLD,SLV", "Alpha Vantage", "M1,M5,M15", "medium", "free_or_premium", "ETF_FALLBACK", "research_only"),
    ("multi", "ETF,FX,Crypto", "Twelve Data", "M1,M5,M15", "medium", "free_or_premium", "UNIFIED_FALLBACK", "research_only"),
    ("fx", "EURUSD", "Twelve Data", "M1,M5,M15", "medium", "free_or_premium", "RECOMMENDED_FX_PRIMARY", "research_only"),
    ("fallback", "ETF,FX", "Yahoo/Stooq", "D1", "low", "free", "DAILY_ONLY_FALLBACK", "research_only"),
]

TARGETS = ["BTCUSD", "ETHUSD", "SPY", "QQQ", "GLD", "SLV", "EURUSD"]

def main():
    print("=== EXTERNAL MARKET DATA SOURCE AUDIT V1 ===")
    print()

    print("TARGET_SYMBOLS")
    for s in TARGETS:
        print(f"TARGET_ROW symbol={s}")

    print()
    print("SOURCE_CANDIDATES")
    for asset_class, symbols, source, intervals, depth, cost, verdict, mode in SOURCES:
        print(
            f"SOURCE_ROW asset_class={asset_class} symbols={symbols} "
            f"source={source!r} intervals={intervals} historical_depth={depth} "
            f"cost={cost} verdict={verdict} mode={mode}"
        )

    print()
    print("RECOMMENDATION")
    print("SOURCE_RECOMMENDED_CRYPTO=Binance public data + REST klines")
    print("SOURCE_RECOMMENDED_ETF=Polygon/Massive primary; Alpha Vantage fallback")
    print("SOURCE_RECOMMENDED_FX=Twelve Data primary")
    print("SOURCE_RECOMMENDED_DAILY_FALLBACK=Yahoo/Stooq")
    print()

    print("ARCHITECTURE_LIMITS")
    print("LIMIT execution=disabled")
    print("LIMIT risk_stack=unchanged")
    print("LIMIT runtime_pipeline=unchanged")
    print("LIMIT storage=postgresql_only")
    print("LIMIT mode=research_only")

    print()
    print("NEXT_STEP=research_market_data_provider_abstraction_v1")
    print("VERDICT=READY_FOR_PROVIDER_ABSTRACTION")


if __name__ == '__main__':
    main()
