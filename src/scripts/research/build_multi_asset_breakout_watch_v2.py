#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime, timezone

import psycopg

from finam_core.strategy.instrument_profile import resolve_instrument_signal_profile


NOW_UTC = datetime.now(timezone.utc)
LOOKBACK_BARS = int(os.getenv("LOOKBACK_BARS", "30"))
FRESH_MINUTES = int(os.getenv("FRESH_MINUTES", "240"))
MIN_BARS = int(os.getenv("MIN_BARS", "30"))
FUTURES_PREFIXES = tuple(
    x.strip().upper()
    for x in os.getenv("FUTURES_PREFIXES", "BR,NG,GD").split(",")
    if x.strip()
)

MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}


def family(symbol: str) -> str:
    s = symbol.upper()
    if s.startswith("BR"):
        return "BRENT_FUTURES"
    if s.startswith("NG"):
        return "GAS_FUTURES"
    if s.startswith("GD"):
        return "GOLD_FUTURES"
    if s.endswith("@MISX"):
        return "EQUITY"
    return "UNKNOWN"


def parse_month(symbol: str) -> tuple[int | None, int | None, str | None]:
    base = symbol.split("@", 1)[0].upper()
    match = re.match(r"^[A-Z]+([FGHJKMNQUVXZ])([0-9])$", base)
    if not match:
        return None, None, None

    code = match.group(1)
    digit = int(match.group(2))
    year = 2020 + digit
    if year < NOW_UTC.year - 1:
        year += 10

    return year, MONTH_CODES.get(code), code


def freshness(last_ts) -> str:
    if last_ts is None:
        return "NO_BARS"
    minutes = (NOW_UTC - last_ts.astimezone(timezone.utc)).total_seconds() / 60.0
    if minutes <= FRESH_MINUTES:
        return "FRESH"
    return "STALE"


def expiry_bucket(symbol: str) -> str:
    year, month, _ = parse_month(symbol)
    if year is None or month is None:
        return "EXPIRY_UNKNOWN"
    if year < NOW_UTC.year or (year == NOW_UTC.year and month < NOW_UTC.month):
        return "EXPIRED"
    if year == NOW_UTC.year and month == NOW_UTC.month:
        return "FRONT"
    if year == NOW_UTC.year and month == NOW_UTC.month + 1:
        return "NEXT"
    return "FAR"


def selected_futures_contracts(cur) -> list[dict]:
    where_parts = []
    params = []
    for prefix in FUTURES_PREFIXES:
        where_parts.append("symbol like %s")
        params.append(f"{prefix}%@RTSX")

    cur.execute(
        f"""
        select
            symbol,
            timeframe,
            count(*)::int as bars,
            max(ts) as last_ts,
            avg(volume) as avg_volume
        from market_bars
        where ({' or '.join(where_parts)})
          and timeframe in ('M1', 'M5')
        group by symbol, timeframe
        order by symbol, timeframe
        """,
        tuple(params),
    )

    raw = []
    for symbol, timeframe, bars, last_ts, avg_volume in cur.fetchall():
        fam = family(symbol)
        fresh = freshness(last_ts)
        exp = expiry_bucket(symbol)
        avg_volume_f = float(avg_volume or 0.0)
        liquidity_score = avg_volume_f * (1.15 if timeframe == "M5" else 1.0)

        candidate = (
            fam in {"BRENT_FUTURES", "GAS_FUTURES", "GOLD_FUTURES"}
            and fresh == "FRESH"
            and exp in {"FRONT", "NEXT", "FAR", "EXPIRY_UNKNOWN"}
            and int(bars or 0) >= MIN_BARS
        )

        raw.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "family": fam,
                "bars": int(bars or 0),
                "last_ts": last_ts,
                "avg_volume": avg_volume_f,
                "liquidity_score": liquidity_score,
                "freshness": fresh,
                "expiry_bucket": exp,
                "candidate": candidate,
            }
        )

    grouped = defaultdict(list)
    for row in raw:
        if row["candidate"]:
            grouped[row["family"]].append(row)

    selected = []
    for fam, rows in grouped.items():
        rows_sorted = sorted(
            rows,
            key=lambda r: (
                {"FRONT": 0, "NEXT": 1, "FAR": 2, "EXPIRY_UNKNOWN": 3}.get(r["expiry_bucket"], 9),
                -r["liquidity_score"],
            ),
        )

        primary = None
        for row in rows_sorted:
            if row["expiry_bucket"] in {"FRONT", "NEXT"}:
                primary = row
                break
        if primary is None and rows_sorted:
            primary = rows_sorted[0]

        if primary:
            selected.append({**primary, "watch_role": "PRIMARY_WATCH", "watch_source": "futures_selection_v1"})

            primary_base = str(primary["symbol"]).split("@", 1)[0]
            for row in rows_sorted:
                row_base = str(row["symbol"]).split("@", 1)[0]
                if row is primary:
                    continue
                if row_base == primary_base and row["timeframe"] == "M1":
                    selected.append({**row, "watch_role": "INTRADAY_WATCH", "watch_source": "futures_selection_v1"})
                    break

        for row in rows_sorted:
            if row is primary:
                continue
            if any(
                row["symbol"] == selected_row["symbol"] and row["timeframe"] == selected_row["timeframe"]
                for selected_row in selected
            ):
                continue
            if row["expiry_bucket"] in {"NEXT", "FAR"}:
                selected.append({**row, "watch_role": "SECONDARY_WATCH", "watch_source": "futures_selection_v1"})
                break

    return selected


def active_equities(cur) -> list[dict]:
    cur.execute(
        """
        select symbol, strategy, timeframe, score, updated_at
        from runtime_active_universe
        where is_enabled = true
          and symbol like %s
        order by symbol
        """,
        ("%@MISX",),
    )

    rows = []
    for symbol, strategy, timeframe, score, updated_at in cur.fetchall():
        rows.append(
            {
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": timeframe or "M5",
                "family": "EQUITY",
                "watch_role": "RUNTIME_EQUITY_WATCH",
                "watch_source": "runtime_active_universe",
                "score": score,
                "updated_at": updated_at,
                "freshness": "RUNTIME",
                "expiry_bucket": "NOT_APPLICABLE",
            }
        )
    return rows


def evaluate_symbol(cur, row: dict) -> dict:
    symbol = row["symbol"]
    timeframe = row["timeframe"]
    profile = resolve_instrument_signal_profile(symbol, timeframe)

    cur.execute(
        """
        select ts, open, high, low, close, volume
        from market_bars
        where symbol = %s
          and timeframe = %s
        order by ts desc
        limit %s
        """,
        (symbol, profile.timeframe, LOOKBACK_BARS + 1),
    )

    raw_rows = cur.fetchall()
    if len(raw_rows) < 2:
        return {
            **row,
            "status": "NO_ENOUGH_BARS",
            "rows": len(raw_rows),
            "asset_class": profile.asset_class,
            "profile_timeframe": profile.timeframe,
            "atr_min_pct": profile.atr_min_pct,
            "volume_mult": profile.volume_mult,
            "use_volume_filter": profile.use_volume_filter,
        }

    bars = list(reversed(raw_rows))
    latest = bars[-1]
    previous = bars[:-1]

    ts, open_, high, low, close, volume = latest
    close_f = float(close or 0.0)
    high_f = float(high or close_f)
    low_f = float(low or close_f)
    volume_f = float(volume or 0.0)

    previous_highs = [float(item[2]) for item in previous if item[2] is not None]
    previous_volumes = [float(item[5] or 0.0) for item in previous]

    prev_high = max(previous_highs) if previous_highs else None
    avg_volume = sum(previous_volumes) / len(previous_volumes) if previous_volumes else 0.0

    atr_abs = max(high_f - low_f, 0.0)
    atr_pct = atr_abs / close_f if close_f else 0.0
    volume_ratio = volume_f / avg_volume if avg_volume else 0.0

    breakout_ok = close_f > prev_high if prev_high is not None else False
    atr_ok = atr_pct >= profile.atr_min_pct
    volume_ok = (
        volume_ratio >= profile.volume_mult
        if profile.use_volume_filter and profile.volume_mult is not None
        else True
    )

    ready = breakout_ok and atr_ok and volume_ok

    if ready:
        status = "BREAKOUT_READY"
    else:
        reasons = []
        if not breakout_ok:
            reasons.append("NO_BREAKOUT")
        if not atr_ok:
            reasons.append("ATR_TOO_LOW")
        if not volume_ok:
            reasons.append("VOLUME_TOO_LOW")
        status = "|".join(reasons)

    return {
        **row,
        "status": status,
        "ready": ready,
        "asset_class": profile.asset_class,
        "profile_timeframe": profile.timeframe,
        "atr_min_pct": profile.atr_min_pct,
        "volume_mult": profile.volume_mult,
        "use_volume_filter": profile.use_volume_filter,
        "ts": ts,
        "close": close_f,
        "prev_high": prev_high,
        "breakout_ok": breakout_ok,
        "atr_pct": atr_pct,
        "atr_ok": atr_ok,
        "volume": volume_f,
        "avg_volume": avg_volume,
        "volume_ratio": volume_ratio,
        "volume_ok": volume_ok,
        "rows": len(raw_rows),
    }


def main() -> int:
    print("=== MULTI ASSET BREAKOUT WATCH V2 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"lookback_bars={LOOKBACK_BARS}")
    print(f"futures_prefixes={','.join(FUTURES_PREFIXES)}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            universe = active_equities(cur) + selected_futures_contracts(cur)

            print()
            print("MULTI_ASSET_BREAKOUT_WATCH_V2_UNIVERSE_ROWS")
            for row in universe:
                print(
                    "MULTI_ASSET_BREAKOUT_WATCH_V2_UNIVERSE_ROW "
                    f"symbol={row['symbol']} family={row['family']} timeframe={row['timeframe']} "
                    f"role={row['watch_role']} source={row['watch_source']} "
                    f"freshness={row.get('freshness')} expiry_bucket={row.get('expiry_bucket')}"
                )

            print()
            print("MULTI_ASSET_BREAKOUT_WATCH_V2_ROWS")

            evaluated = []
            for row in universe:
                result = evaluate_symbol(cur, row)
                evaluated.append(result)

                if result["status"] == "NO_ENOUGH_BARS":
                    print(
                        "MULTI_ASSET_BREAKOUT_WATCH_V2_ROW "
                        f"symbol={result['symbol']} asset_class={result['asset_class']} "
                        f"timeframe={result['profile_timeframe']} role={result['watch_role']} "
                        f"status=NO_ENOUGH_BARS rows={result['rows']}"
                    )
                    continue

                print(
                    "MULTI_ASSET_BREAKOUT_WATCH_V2_ROW "
                    f"symbol={result['symbol']} asset_class={result['asset_class']} "
                    f"timeframe={result['profile_timeframe']} role={result['watch_role']} "
                    f"ts={result['ts']} close={result['close']:.6f} "
                    f"prev_high={result['prev_high']} breakout_ok={int(result['breakout_ok'])} "
                    f"atr_pct={result['atr_pct']:.8f} atr_min_pct={result['atr_min_pct']:.8f} "
                    f"atr_ok={int(result['atr_ok'])} volume={result['volume']:.2f} "
                    f"avg_volume={result['avg_volume']:.2f} volume_ratio={result['volume_ratio']:.6f} "
                    f"volume_mult={result['volume_mult'] if result['volume_mult'] is not None else 'None'} "
                    f"volume_ok={int(result['volume_ok'])} status={result['status']}"
                )

    rows_total = sum(1 for row in evaluated if row["status"] != "NO_ENOUGH_BARS")
    no_bars = sum(1 for row in evaluated if row["status"] == "NO_ENOUGH_BARS")
    ready = sum(1 for row in evaluated if row.get("ready"))
    futures_rows = sum(1 for row in evaluated if row.get("family") in {"BRENT_FUTURES", "GAS_FUTURES", "GOLD_FUTURES"})
    equity_rows = sum(1 for row in evaluated if row.get("family") == "EQUITY")
    no_breakout = sum(1 for row in evaluated if "NO_BREAKOUT" in row.get("status", ""))
    atr_blocked = sum(1 for row in evaluated if "ATR_TOO_LOW" in row.get("status", ""))
    volume_blocked = sum(1 for row in evaluated if "VOLUME_TOO_LOW" in row.get("status", ""))

    print()
    print("MULTI_ASSET_BREAKOUT_WATCH_V2_SUMMARY")
    print(f"universe_total={len(universe)}")
    print(f"rows_total={rows_total}")
    print(f"equity_rows={equity_rows}")
    print(f"futures_rows={futures_rows}")
    print(f"no_bars={no_bars}")
    print(f"breakout_ready={ready}")
    print(f"no_breakout={no_breakout}")
    print(f"atr_blocked={atr_blocked}")
    print(f"volume_blocked={volume_blocked}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if ready > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_WATCH_V2_HAS_READY_SETUPS")
    elif rows_total > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_WATCH_V2_NO_READY_SETUPS")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_WATCH_V2_NO_EVALUATED_ROWS")

    print("MULTI_ASSET_BREAKOUT_WATCH_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
