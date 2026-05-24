from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo


UTC = ZoneInfo("UTC")
MSK = ZoneInfo("Europe/Moscow")
NY = ZoneInfo("America/New_York")


def _aware_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _between(t: time, start: time, end: time) -> bool:
    return start <= t < end


def classify_futures_session(ts: datetime) -> str:
    """
    Русский комментарий:
    Классификатор торговых сессий фьючерсов.
    MOEX считаем по MSK.
    US_OPEN_WINDOW считаем по New York time с учетом DST.
    На выходных для срочного рынка учитываем окно 10:00–19:00 МСК.
    """

    utc = _aware_utc(ts)
    msk = utc.astimezone(MSK)
    ny = utc.astimezone(NY)

    msk_t = msk.time()
    ny_t = ny.time()

    if msk.weekday() in (5, 6):
        if _between(msk_t, time(10, 0), time(19, 0)):
            return "MOEX_WEEKEND_DAY"
        return "WEEKEND"

    if _between(msk_t, time(9, 0), time(10, 0)):
        return "MOEX_MORNING"

    if _between(ny_t, time(9, 30), time(11, 30)):
        return "US_OPEN_WINDOW"

    if _between(msk_t, time(10, 0), time(19, 0)):
        return "MOEX_DAY"

    if _between(msk_t, time(19, 0), time(23, 50)):
        return "MOEX_EVENING"

    return "CLOSED"
