from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKET_STRUCTURE_ENGINE_V1"


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def parse_decimal_list(value: str) -> list[Decimal]:
    return [Decimal(x.strip()) for x in value.split(",") if x.strip()]


def load_parameters(cur) -> dict[str, Any]:
    cur.execute("""
        SELECT parameter_code, parameter_type, parameter_value
        FROM knowledge.platform_parameter_v1
        WHERE enabled
          AND parameter_group='MARKET_STRUCTURE'
    """)
    result: dict[str, Any] = {}
    for row in cur.fetchall():
        code = row["parameter_code"]
        value = row["parameter_value"]
        ptype = row["parameter_type"]

        if ptype == "INTEGER":
            result[code] = int(Decimal(str(value)))
        elif ptype == "NUMERIC":
            result[code] = Decimal(str(value))
        else:
            result[code] = str(value)

    return result


def enabled_types(cur) -> set[str]:
    cur.execute("""
        SELECT structure_type_code
        FROM knowledge.market_structure_type_v1
        WHERE enabled
    """)
    return {str(r["structure_type_code"]) for r in cur.fetchall()}


def load_symbols(cur) -> list[dict[str, str]]:
    cur.execute("""
        SELECT DISTINCT symbol, timeframe
        FROM public.market_bars
        WHERE close IS NOT NULL
          AND high IS NOT NULL
          AND low IS NOT NULL
        ORDER BY symbol, timeframe
    """)
    return [{"symbol": r["symbol"], "timeframe": r["timeframe"]} for r in cur.fetchall()]


def load_bars(cur, symbol: str, timeframe: str, lookback: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT ts, open, high, low, close
        FROM public.market_bars
        WHERE symbol=%s
          AND timeframe=%s
          AND close IS NOT NULL
          AND high IS NOT NULL
          AND low IS NOT NULL
        ORDER BY ts DESC
        LIMIT %s
        """,
        (symbol, timeframe, lookback),
    )
    return list(reversed(cur.fetchall()))


def insert_level(
    cur,
    symbol: str,
    timeframe: str,
    structure_type: str,
    price: Decimal,
    strength: Decimal,
    lookback: int,
    detected_at: Any,
    evidence: dict[str, Any],
) -> None:
    cur.execute(
        """
        INSERT INTO knowledge.market_structure_v1
        (
            symbol,
            timeframe,
            structure_type_code,
            level_price,
            level_strength,
            lookback_bars,
            detected_at,
            evidence_json,
            source_version
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
        """,
        (
            symbol,
            timeframe,
            structure_type,
            price,
            strength,
            lookback,
            detected_at,
            json.dumps(evidence, ensure_ascii=False),
            SOURCE_VERSION,
        ),
    )


def find_swings(bars: list[dict[str, Any]], window: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    highs: list[dict[str, Any]] = []
    lows: list[dict[str, Any]] = []

    if len(bars) < (window * 2 + 1):
        return highs, lows

    for idx in range(window, len(bars) - window):
        current = bars[idx]
        high = to_decimal(current["high"])
        low = to_decimal(current["low"])
        if high is None or low is None:
            continue

        left = bars[idx - window:idx]
        right = bars[idx + 1:idx + window + 1]

        is_high = all(high >= to_decimal(x["high"]) for x in left + right if to_decimal(x["high"]) is not None)
        is_low = all(low <= to_decimal(x["low"]) for x in left + right if to_decimal(x["low"]) is not None)

        if is_high:
            highs.append({"ts": current["ts"], "price": high})
        if is_low:
            lows.append({"ts": current["ts"], "price": low})

    return highs, lows


def build_for_symbol(
    cur,
    symbol: str,
    timeframe: str,
    params: dict[str, Any],
    types: set[str],
) -> int:
    lookback = int(params["MARKET_STRUCTURE_LOOKBACK_BARS"])
    window = int(params["MARKET_STRUCTURE_SWING_WINDOW"])
    fib_retracements = parse_decimal_list(str(params["MARKET_STRUCTURE_FIB_RETRACEMENTS"]))
    fib_extensions = parse_decimal_list(str(params["MARKET_STRUCTURE_FIB_EXTENSIONS"]))

    bars = load_bars(cur, symbol, timeframe, lookback)
    if len(bars) < (window * 2 + 1):
        return 0

    latest = bars[-1]
    latest_close = to_decimal(latest["close"])
    detected_at = latest["ts"]
    if latest_close is None:
        return 0

    swing_highs, swing_lows = find_swings(bars, window)
    inserted = 0

    if swing_highs and "SWING_HIGH" in types:
        last_high = swing_highs[-1]
        insert_level(
            cur, symbol, timeframe, "SWING_HIGH",
            last_high["price"], Decimal(len(swing_highs)), lookback, last_high["ts"],
            {"method": "local_extrema", "window": window, "role": "swing_high"},
        )
        inserted += 1

    if swing_lows and "SWING_LOW" in types:
        last_low = swing_lows[-1]
        insert_level(
            cur, symbol, timeframe, "SWING_LOW",
            last_low["price"], Decimal(len(swing_lows)), lookback, last_low["ts"],
            {"method": "local_extrema", "window": window, "role": "swing_low"},
        )
        inserted += 1

    supports = [x for x in swing_lows if x["price"] <= latest_close]
    resistances = [x for x in swing_highs if x["price"] >= latest_close]

    if supports and "SUPPORT" in types:
        support = max(supports, key=lambda x: x["price"])
        insert_level(
            cur, symbol, timeframe, "SUPPORT",
            support["price"], Decimal(len(supports)), lookback, detected_at,
            {"method": "nearest_swing_low_below_close", "latest_close": str(latest_close)},
        )
        inserted += 1

    if resistances and "RESISTANCE" in types:
        resistance = min(resistances, key=lambda x: x["price"])
        insert_level(
            cur, symbol, timeframe, "RESISTANCE",
            resistance["price"], Decimal(len(resistances)), lookback, detected_at,
            {"method": "nearest_swing_high_above_close", "latest_close": str(latest_close)},
        )
        inserted += 1

    if "PIVOT_LEVEL" in types:
        high = to_decimal(latest["high"])
        low = to_decimal(latest["low"])
        close = to_decimal(latest["close"])
        if high is not None and low is not None and close is not None:
            pivot = (high + low + close) / Decimal("3")
            insert_level(
                cur, symbol, timeframe, "PIVOT_LEVEL",
                pivot, Decimal("1"), lookback, detected_at,
                {"method": "classic_hlc_pivot", "bar_ts": str(detected_at)},
            )
            inserted += 1

    if swing_highs and swing_lows:
        high = swing_highs[-1]["price"]
        low = swing_lows[-1]["price"]
        price_range = abs(high - low)

        if price_range > 0:
            for ratio in fib_retracements:
                if "FIBONACCI_RETRACEMENT" not in types:
                    continue
                level = high - (price_range * ratio) if high >= low else low - (price_range * ratio)
                insert_level(
                    cur, symbol, timeframe, "FIBONACCI_RETRACEMENT",
                    level, ratio, lookback, detected_at,
                    {
                        "method": "last_swing_range",
                        "ratio": str(ratio),
                        "swing_high": str(high),
                        "swing_low": str(low),
                    },
                )
                inserted += 1

            for ratio in fib_extensions:
                if "FIBONACCI_EXTENSION" not in types:
                    continue
                level = high + (price_range * (ratio - Decimal("1"))) if high >= low else low + (price_range * (ratio - Decimal("1")))
                insert_level(
                    cur, symbol, timeframe, "FIBONACCI_EXTENSION",
                    level, ratio, lookback, detected_at,
                    {
                        "method": "last_swing_range",
                        "ratio": str(ratio),
                        "swing_high": str(high),
                        "swing_low": str(low),
                    },
                )
                inserted += 1

    if swing_highs and "CHANNEL_UPPER" in types:
        upper = max(x["price"] for x in swing_highs[-min(len(swing_highs), 3):])
        insert_level(
            cur, symbol, timeframe, "CHANNEL_UPPER",
            upper, Decimal("1"), lookback, detected_at,
            {"method": "recent_swing_high_band"},
        )
        inserted += 1

    if swing_lows and "CHANNEL_LOWER" in types:
        lower = min(x["price"] for x in swing_lows[-min(len(swing_lows), 3):])
        insert_level(
            cur, symbol, timeframe, "CHANNEL_LOWER",
            lower, Decimal("1"), lookback, detected_at,
            {"method": "recent_swing_low_band"},
        )
        inserted += 1

    if swing_highs and "BREAKOUT_LEVEL" in types:
        breakout = max(x["price"] for x in swing_highs[-min(len(swing_highs), 3):])
        insert_level(
            cur, symbol, timeframe, "BREAKOUT_LEVEL",
            breakout, Decimal("1"), lookback, detected_at,
            {"method": "recent_swing_high_breakout"},
        )
        inserted += 1

    return inserted


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            params = load_parameters(cur)
            required = {
                "MARKET_STRUCTURE_LOOKBACK_BARS",
                "MARKET_STRUCTURE_SWING_WINDOW",
                "MARKET_STRUCTURE_FIB_RETRACEMENTS",
                "MARKET_STRUCTURE_FIB_EXTENSIONS",
            }
            missing = required - set(params)
            if missing:
                raise RuntimeError(f"missing market structure parameters: {sorted(missing)}")

            types = enabled_types(cur)
            symbols = load_symbols(cur)

            inserted_total = 0
            processed = 0

            for item in symbols:
                inserted_total += build_for_symbol(
                    cur,
                    item["symbol"],
                    item["timeframe"],
                    params,
                    types,
                )
                processed += 1

    print("=== MARKET_STRUCTURE_ENGINE_V1 ===")
    print(f"symbol_timeframes_processed={processed}")
    print(f"structure_rows_inserted={inserted_total}")
    print("config_source=postgres")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_STRUCTURE_ENGINE_V1_READY")


if __name__ == "__main__":
    main()
