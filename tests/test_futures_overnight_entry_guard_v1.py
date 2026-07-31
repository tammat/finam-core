from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.pipelines.paper_pipeline import futures_overnight_entry_guard_v1


MSK = ZoneInfo("Europe/Moscow")


def decision(hour: int, minute: int, *, symbol="BRQ6@RTSX", intent="ENTRY"):
    return futures_overnight_entry_guard_v1(
        symbol=symbol, intent_type=intent,
        now_msk=datetime(2026, 7, 31, hour, minute, tzinfo=MSK),
    )


def test_blocks_new_futures_entry_before_overnight_gap() -> None:
    assert decision(22, 29)[0]
    assert decision(22, 30) == (False, "FUTURES_OVERNIGHT_GAP_RISK")
    assert decision(23, 0) == (False, "FUTURES_OVERNIGHT_GAP_RISK")
    assert decision(6, 59) == (False, "FUTURES_OVERNIGHT_GAP_RISK")


def test_never_blocks_exit_or_equity() -> None:
    assert decision(23, 30, intent="EXIT")[0]
    assert decision(23, 30, symbol="GAZP@MISX")[0]
