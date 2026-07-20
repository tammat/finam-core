from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
MSK = ZoneInfo("Europe/Moscow")
SOURCE = "MARKET_OPEN_READINESS_V1"
M1_MAX_AGE_SECONDS = int(os.getenv("MARKET_READINESS_M1_MAX_AGE_SECONDS", "180"))
M5_MAX_AGE_SECONDS = int(os.getenv("MARKET_READINESS_M5_MAX_AGE_SECONDS", "480"))


def _age(now: datetime, value: datetime | None) -> int | None:
    return max(0, int((now - value).total_seconds())) if value else None


def quotes_are_fresh(m1_age: int | None, m5_age: int | None) -> bool:
    """M5 includes its five-minute bar duration; M1 is the fast liveness probe."""
    return bool(
        (m1_age is not None and m1_age <= M1_MAX_AGE_SECONDS)
        or (m5_age is not None and m5_age <= M5_MAX_AGE_SECONDS)
    )


def _next_session(cursor, now: datetime) -> datetime | None:
    for days in range(8):
        date = (now + timedelta(days=days)).date()
        cursor.execute("""SELECT enabled,opens_at FROM analytics.market_session_policy_v1
                          WHERE weekday_iso=extract(isodow from %s::date)""", (date,))
        row = cursor.fetchone()
        if not row or not row["enabled"]:
            continue
        candidate = datetime.combine(date, row["opens_at"], tzinfo=MSK)
        if candidate > now:
            return candidate
    return None


def main() -> int:
    now = datetime.now(MSK)
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT enabled,opens_at,closes_at
                FROM analytics.market_session_policy_v1 WHERE weekday_iso=%s""", (now.isoweekday(),))
            policy = cursor.fetchone() or {}
            opened = bool(policy.get("enabled") and policy["opens_at"] <= now.time().replace(tzinfo=None) < policy["closes_at"])
            cursor.execute("""SELECT
                (SELECT max(ts) FROM public.market_bars WHERE timeframe='M1') quote_m1_ts,
                (SELECT max(ts) FROM public.market_bars WHERE timeframe='M5') quote_m5_ts,
                (SELECT max(created_at) FROM public.runtime_guard_signal_registry_v1) signal_ts,
                (SELECT max(ts) FROM public.fills) fill_ts,
                (SELECT count(*) FROM analytics.signal_intake_queue_v2 WHERE status_code IN ('PENDING','RUNNING')) pending""")
            data = cursor.fetchone()
            quote_m1_age = _age(now, data["quote_m1_ts"])
            quote_m5_age = _age(now, data["quote_m5_ts"])
            quote_ages = [age for age in (quote_m1_age, quote_m5_age) if age is not None]
            quote_age = min(quote_ages) if quote_ages else None
            signal_age, fill_age = (_age(now, data[key]) for key in ("signal_ts","fill_ts"))
            if not opened:
                phase, status, reason = "WAITING", "WAITING", "MARKET_SESSION_CLOSED"
            elif not quotes_are_fresh(quote_m1_age, quote_m5_age):
                phase, status, reason = "QUOTES", "FAILED", "QUOTES_NOT_FRESH"
            elif signal_age is None or signal_age > 1800:
                phase, status, reason = "SIGNALS", "ATTENTION", "SIGNALS_NOT_CREATED_YET"
            elif fill_age is None or fill_age > 3600:
                phase, status, reason = "TRADES", "ATTENTION", "FILLS_NOT_CREATED_YET"
            else:
                phase, status, reason = "RESEARCH", "HEALTHY", "LIVE_CHAIN_HEALTHY"
            next_session = _next_session(cursor, now) if not opened else None
            cursor.execute("""INSERT INTO analytics.market_open_readiness_v1(
                check_id,phase_code,status_code,session_open,quote_age_seconds,
                signal_age_seconds,fill_age_seconds,pending_signals,reason_code,next_session_at,source_version)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (str(uuid.uuid4()),phase,status,opened,quote_age,signal_age,fill_age,
                 int(data["pending"] or 0),reason,next_session,SOURCE))
    print(f"phase={phase}")
    print(f"status={status}")
    print(f"reason={reason}")
    print("live_allowed=0")
    print("VERDICT=MARKET_OPEN_READINESS_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
