from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NgContractWindow:
    symbol: str
    start: datetime
    end: datetime


NG_CONTRACT_WINDOWS = {
    "NGM6@RTSX": NgContractWindow("NGM6@RTSX", datetime(2026, 3, 1, tzinfo=timezone.utc), datetime(2026, 6, 30, tzinfo=timezone.utc)),
    "NGN6@RTSX": NgContractWindow("NGN6@RTSX", datetime(2026, 4, 1, tzinfo=timezone.utc), datetime(2026, 7, 31, tzinfo=timezone.utc)),
    "NGQ6@RTSX": NgContractWindow("NGQ6@RTSX", datetime(2026, 5, 1, tzinfo=timezone.utc), datetime(2026, 8, 31, tzinfo=timezone.utc)),
    "NGU6@RTSX": NgContractWindow("NGU6@RTSX", datetime(2026, 6, 1, tzinfo=timezone.utc), datetime(2026, 9, 30, tzinfo=timezone.utc)),
    "NGV6@RTSX": NgContractWindow("NGV6@RTSX", datetime(2026, 7, 1, tzinfo=timezone.utc), datetime(2026, 10, 31, tzinfo=timezone.utc)),
    "NGX6@RTSX": NgContractWindow("NGX6@RTSX", datetime(2026, 8, 1, tzinfo=timezone.utc), datetime(2026, 11, 30, tzinfo=timezone.utc)),
    "NGZ6@RTSX": NgContractWindow("NGZ6@RTSX", datetime(2026, 9, 1, tzinfo=timezone.utc), datetime(2026, 12, 31, tzinfo=timezone.utc)),
}


def get_ng_contract_window(symbol: str) -> NgContractWindow:
    return NG_CONTRACT_WINDOWS[symbol]


def get_ng_symbols() -> list[str]:
    return list(NG_CONTRACT_WINDOWS.keys())
