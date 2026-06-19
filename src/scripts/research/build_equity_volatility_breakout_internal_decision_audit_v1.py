#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path

import psycopg


ROOT = Path("/opt/finam-core")
ACTIVE_SINCE_UTC = os.getenv("ACTIVE_SINCE_UTC", "2026-06-19 07:24:35+00")
LOOKBACK_BARS = int(os.getenv("LOOKBACK_BARS", "30"))
BAR_TIMEFRAME = os.getenv("BAR_TIMEFRAME", "M5")
STRATEGY_FILE = None


def discover_strategy_file() -> Path:
    """Русский комментарий: ищем фактический файл стратегии без жёсткой привязки к каталогу."""
    candidates = []

    for base in (
        ROOT / "src/finam_core",
        ROOT / "src/core",
        ROOT / "src",
    ):
        if not base.exists():
            continue

        for path in base.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            if "class VolatilityBreakoutEquity" in text:
                return path

            if "VOLATILITY_BREAKOUT_EQUITY" in text and "on_quote" in text:
                candidates.append(path)

    if candidates:
        return candidates[0]

    raise FileNotFoundError("VolatilityBreakoutEquity source file not found")


def read_strategy_source() -> tuple[Path, str]:
    strategy_file = discover_strategy_file()
    return strategy_file, strategy_file.read_text(encoding="utf-8", errors="replace")


def extract_default_float(source: str, name: str) -> str:
    patterns = [
        rf"{name}\s*:\s*float\s*=\s*([0-9.]+)",
        rf"{name}\s*=\s*([0-9.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, source)
        if match:
            return match.group(1)
    return "UNKNOWN"


def main() -> int:
    print("=== EQUITY VOLATILITY BREAKOUT INTERNAL DECISION AUDIT V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print(f"active_since_utc={ACTIVE_SINCE_UTC}")
    print(f"timeframe={BAR_TIMEFRAME}")
    print(f"lookback_bars={LOOKBACK_BARS}")

    strategy_file, source = read_strategy_source()

    min_atr_pct = extract_default_float(source, "min_atr_pct")
    volume_mult = extract_default_float(source, "volume_mult")
    breakout_lookback = extract_default_float(source, "lookback")

    print()
    print("EQUITY_VOL_BREAKOUT_SOURCE_PARAMS")
    print(f"source_file={strategy_file}")
    print(f"default_min_atr_pct={min_atr_pct}")
    print(f"default_volume_mult={volume_mult}")
    print(f"default_lookback={breakout_lookback}")
    print(f"has_on_quote={int('def on_quote' in source)}")
    print(f"has_signal_return={int('return' in source and 'Signal' in source)}")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select symbol, strategy, timeframe, is_enabled, score, updated_at
                from runtime_active_universe
                where is_enabled = true
                  and symbol like %s
                  and strategy = 'VOLATILITY_BREAKOUT_EQUITY'
                order by symbol
                """,
                ("%@MISX",),
            )
            runtime_rows = cur.fetchall()

            print()
            print("EQUITY_VOL_BREAKOUT_RUNTIME_ROWS")
            for row in runtime_rows:
                print(
                    "EQUITY_VOL_BREAKOUT_RUNTIME_ROW "
                    f"symbol={row[0]} strategy={row[1]} timeframe={row[2]} "
                    f"is_enabled={int(bool(row[3]))} score={row[4]} updated_at={row[5]}"
                )

            print()
            print("EQUITY_VOL_BREAKOUT_BAR_DECISION_ROWS")

            blocked_by_atr = 0
            blocked_by_volume = 0
            blocked_by_breakout = 0
            rows_total = 0
            ready_rows = 0

            for runtime_row in runtime_rows:
                symbol = runtime_row[0]

                cur.execute(
                    """
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                      and ts <= %s::timestamptz
                    order by ts desc
                    limit %s
                    """,
                    (symbol, BAR_TIMEFRAME, ACTIVE_SINCE_UTC, LOOKBACK_BARS),
                )
                historical_rows = list(reversed(cur.fetchall()))

                cur.execute(
                    """
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                      and ts > %s::timestamptz
                    order by ts asc
                    limit 20
                    """,
                    (symbol, BAR_TIMEFRAME, ACTIVE_SINCE_UTC),
                )
                fresh_rows = cur.fetchall()

                if not fresh_rows:
                    print(
                        "EQUITY_VOL_BREAKOUT_BAR_DECISION_ROW "
                        f"symbol={symbol} status=NO_FRESH_BARS_AFTER_RESTART"
                    )
                    continue

                history = historical_rows[:]
                for ts, open_, high, low, close, volume in fresh_rows:
                    rows_total += 1

                    previous = history[-LOOKBACK_BARS:] if history else []
                    previous_highs = [float(row[2]) for row in previous if row[2] is not None]
                    previous_volumes = [float(row[5] or 0.0) for row in previous]

                    close_f = float(close or 0.0)
                    high_f = float(high or close_f)
                    low_f = float(low or close_f)
                    volume_f = float(volume or 0.0)

                    atr_abs = max(high_f - low_f, 0.0)
                    atr_pct = atr_abs / close_f if close_f else 0.0
                    prev_high = max(previous_highs) if previous_highs else None
                    avg_volume = (
                        sum(previous_volumes) / len(previous_volumes)
                        if previous_volumes
                        else 0.0
                    )
                    volume_ratio = volume_f / avg_volume if avg_volume else 0.0

                    min_atr_value = float(min_atr_pct) if min_atr_pct != "UNKNOWN" else 0.0
                    volume_mult_value = float(volume_mult) if volume_mult != "UNKNOWN" else 0.0

                    atr_ok = atr_pct >= min_atr_value if min_atr_value > 0 else True
                    volume_ok = volume_ratio >= volume_mult_value if volume_mult_value > 0 else True
                    breakout_ok = close_f > prev_high if prev_high is not None else False

                    if not atr_ok:
                        blocked_by_atr += 1
                    if not volume_ok:
                        blocked_by_volume += 1
                    if not breakout_ok:
                        blocked_by_breakout += 1
                    if atr_ok and volume_ok and breakout_ok:
                        ready_rows += 1

                    reason_parts = []
                    if not atr_ok:
                        reason_parts.append("ATR_TOO_LOW")
                    if not volume_ok:
                        reason_parts.append("VOLUME_TOO_LOW")
                    if not breakout_ok:
                        reason_parts.append("NO_BREAKOUT")
                    if not reason_parts:
                        reason_parts.append("SIGNAL_CONDITIONS_PASSED_BY_PROXY")

                    print(
                        "EQUITY_VOL_BREAKOUT_BAR_DECISION_ROW "
                        f"symbol={symbol} ts={ts} close={close_f:.6f} "
                        f"atr_pct={atr_pct:.8f} min_atr_pct={min_atr_value:.8f} atr_ok={int(atr_ok)} "
                        f"volume={volume_f:.2f} avg_volume={avg_volume:.2f} "
                        f"volume_ratio={volume_ratio:.6f} volume_mult={volume_mult_value:.6f} volume_ok={int(volume_ok)} "
                        f"prev_high={prev_high} breakout_ok={int(breakout_ok)} "
                        f"decision={'|'.join(reason_parts)}"
                    )

                    history.append((ts, open_, high, low, close, volume))

    print()
    print("EQUITY_VOL_BREAKOUT_INTERNAL_DECISION_AUDIT_SUMMARY")
    print(f"runtime_rows={len(runtime_rows)}")
    print(f"rows_total={rows_total}")
    print(f"blocked_by_atr={blocked_by_atr}")
    print(f"blocked_by_volume={blocked_by_volume}")
    print(f"blocked_by_breakout={blocked_by_breakout}")
    print(f"proxy_ready_rows={ready_rows}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if rows_total == 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_NO_FRESH_BARS_FOR_DECISION")
    elif ready_rows > 0:
        print("VERDICT=EQUITY_VOL_BREAKOUT_PROXY_CONDITIONS_PASS_BUT_STRATEGY_NO_SIGNAL")
    elif blocked_by_atr >= blocked_by_volume and blocked_by_atr >= blocked_by_breakout:
        print("VERDICT=EQUITY_VOL_BREAKOUT_BLOCKED_MAINLY_BY_ATR")
    elif blocked_by_volume >= blocked_by_atr and blocked_by_volume >= blocked_by_breakout:
        print("VERDICT=EQUITY_VOL_BREAKOUT_BLOCKED_MAINLY_BY_VOLUME")
    else:
        print("VERDICT=EQUITY_VOL_BREAKOUT_BLOCKED_MAINLY_BY_BREAKOUT_CONDITION")

    print("EQUITY_VOLATILITY_BREAKOUT_INTERNAL_DECISION_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
