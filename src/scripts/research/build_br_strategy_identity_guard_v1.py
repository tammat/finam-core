from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timezone

import psycopg


SYMBOL = "BRM6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"

TARGET_REGIME = "LOW_IMPULSE"
TARGET_TREND = "down"
TARGET_VOLATILITY = "high"

ALLOW_SESSIONS = {"ASIA", "EUROPE"}
BLOCK_SESSIONS = {"US_OPEN"}

ALLOW_DURATION_BUCKETS = {"SCALP_LT_5M"}
WATCH_DURATION_BUCKETS = {"FAST_5_15M"}

ALLOW_MOVE_BUCKETS = {"MEDIUM_MOVE"}
WATCH_MOVE_BUCKETS = {"LARGE_MOVE"}

REPEATABILITY_CONFIRMED = False


@dataclass(frozen=True)
class Metrics:
    trades: int
    passed: int
    watch: int
    failed: int


def classify_session(hour: int) -> str:
    if 0 <= hour < 10:
        return "ASIA"
    if 10 <= hour < 15:
        return "EUROPE"
    if 15 <= hour < 19:
        return "US_OPEN"
    return "US_LATE"


def duration_bucket(minutes: float) -> str:
    if minutes < 5:
        return "SCALP_LT_5M"
    if minutes < 15:
        return "FAST_5_15M"
    if minutes < 60:
        return "INTRADAY_15_60M"
    if minutes < 240:
        return "SWING_1_4H"
    return "LONG_GT_4H"


def move_bucket(value: float) -> str:
    if value <= 0.05:
        return "TINY_MOVE"
    if value <= 0.15:
        return "SMALL_MOVE"
    if value <= 0.35:
        return "MEDIUM_MOVE"
    if value <= 0.70:
        return "LARGE_MOVE"
    return "EXTREME_MOVE"


def identity_decision(
    *,
    regime: str,
    trend: str,
    volatility: str,
    session: str,
    duration: str,
    move: str,
) -> tuple[str, str]:
    reasons: list[str] = []

    if regime != TARGET_REGIME:
        reasons.append(f"regime_mismatch:{regime}")

    if trend != TARGET_TREND:
        reasons.append(f"trend_mismatch:{trend}")

    if volatility != TARGET_VOLATILITY:
        reasons.append(f"volatility_mismatch:{volatility}")

    if session in BLOCK_SESSIONS:
        reasons.append(f"blocked_session:{session}")
    elif session not in ALLOW_SESSIONS:
        reasons.append(f"unknown_session:{session}")

    if duration not in ALLOW_DURATION_BUCKETS:
        if duration in WATCH_DURATION_BUCKETS:
            reasons.append(f"watch_duration:{duration}")
        else:
            reasons.append(f"duration_identity_violation:{duration}")

    if move not in ALLOW_MOVE_BUCKETS:
        if move in WATCH_MOVE_BUCKETS:
            reasons.append(f"watch_move_bucket:{move}")
        else:
            reasons.append(f"move_identity_violation:{move}")

    hard_fail = any(
        item.startswith((
            "regime_mismatch:",
            "trend_mismatch:",
            "volatility_mismatch:",
            "blocked_session:",
            "unknown_session:",
            "duration_identity_violation:",
            "move_identity_violation:",
        ))
        for item in reasons
    )

    if hard_fail:
        return "FAIL", ";".join(reasons)

    if reasons:
        return "WATCH", ";".join(reasons)

    return "PASS", "identity_profile_matched"


def main() -> int:
    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH fs AS (
        SELECT
            symbol,
            timeframe,
            ts,
            close,
            LAG(close) OVER (
                PARTITION BY symbol, timeframe
                ORDER BY ts
            ) AS prev_close
        FROM feature_snapshots
        WHERE symbol = %(symbol)s
          AND timeframe = 'M5'
    ),
    base AS (
        SELECT
            tcs.closed_trade_id,
            COALESCE(tcs.exit_ts, tcs.entry_ts) AS trade_ts,
            tcs.regime,
            tcs.trend,
            tcs.volatility,
            EXTRACT(EPOCH FROM (tcs.exit_ts - tcs.entry_ts)) / 60.0 AS duration_minutes
        FROM trade_context_snapshots tcs
        WHERE tcs.symbol = %(symbol)s
          AND tcs.strategy = %(strategy)s
          AND tcs.context_quality = 'FULL'
          AND tcs.entry_ts IS NOT NULL
          AND tcs.exit_ts IS NOT NULL
    )
    SELECT
        b.closed_trade_id,
        b.trade_ts,
        b.regime,
        b.trend,
        b.volatility,
        b.duration_minutes,
        CASE
            WHEN f.prev_close IS NULL OR f.prev_close = 0 THEN 0
            ELSE ABS(f.close - f.prev_close) / f.prev_close * 100.0
        END AS move_pct
    FROM base b
    JOIN LATERAL (
        SELECT *
        FROM fs
        WHERE fs.ts <= b.trade_ts
          AND fs.prev_close IS NOT NULL
        ORDER BY fs.ts DESC
        LIMIT 1
    ) f ON TRUE
    ORDER BY b.trade_ts ASC, b.closed_trade_id ASC;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"symbol": SYMBOL, "strategy": STRATEGY})
            rows = cur.fetchall()

    print("BR_STRATEGY_IDENTITY_GUARD_V1")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(
        "target_profile="
        f"regime={TARGET_REGIME};trend={TARGET_TREND};volatility={TARGET_VOLATILITY};"
        "sessions=ASIA,EUROPE;duration=SCALP_LT_5M;move=MEDIUM_MOVE"
    )
    print(f"repeatability_confirmed={str(REPEATABILITY_CONFIRMED).lower()}")
    print("closed_trade_id | session | duration_bucket | move_bucket | decision | reason")

    passed = 0
    watch = 0
    failed = 0

    for row in rows:
        closed_trade_id = int(row[0])
        trade_ts = row[1]
        regime = str(row[2] or "unknown")
        trend = str(row[3] or "unknown")
        volatility = str(row[4] or "unknown")
        duration = duration_bucket(float(row[5] or 0.0))
        move = move_bucket(float(row[6] or 0.0))

        if trade_ts.tzinfo is None:
            trade_ts = trade_ts.replace(tzinfo=timezone.utc)

        session = classify_session(int(trade_ts.hour))

        decision, reason = identity_decision(
            regime=regime,
            trend=trend,
            volatility=volatility,
            session=session,
            duration=duration,
            move=move,
        )

        if decision == "PASS":
            passed += 1
        elif decision == "WATCH":
            watch += 1
        else:
            failed += 1

        print(
            f"{closed_trade_id} | "
            f"{session} | "
            f"{duration} | "
            f"{move} | "
            f"{decision} | "
            f"{reason}"
        )

    total = len(rows)
    pass_ratio = passed / total if total else 0.0
    fail_ratio = failed / total if total else 0.0

    if not REPEATABILITY_CONFIRMED:
        verdict = "IDENTITY_RESEARCH_ONLY_REPEATABILITY_NOT_CONFIRMED"
    elif pass_ratio >= 0.60 and fail_ratio <= 0.25:
        verdict = "IDENTITY_PROFILE_USABLE"
    elif pass_ratio >= 0.40:
        verdict = "IDENTITY_PROFILE_WATCH"
    else:
        verdict = "IDENTITY_PROFILE_BROKEN"

    print("SUMMARY")
    print(f"total={total}")
    print(f"passed={passed}")
    print(f"watch={watch}")
    print(f"failed={failed}")
    print(f"pass_ratio={pass_ratio:.6f}")
    print(f"fail_ratio={fail_ratio:.6f}")
    print(f"verdict={verdict}")
    print(
        "BR_STRATEGY_IDENTITY_GUARD_V1_OK "
        f"total={total} "
        f"verdict={verdict}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
