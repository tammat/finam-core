from datetime import datetime, time
from zoneinfo import ZoneInfo
from scripts.market_session_regime_v1 import classify_market_session

def test_us_open_is_dst_aware():
    policies=({"session_code":"US_OPEN","timezone_code":"America/New_York",
        "local_start":time(9,20),"local_end":time(10,30),"weekdays":[1,2,3,4,5],"priority":100},)
    assert classify_market_session(datetime(2026,7,20,9,30,tzinfo=ZoneInfo("America/New_York")),policies)=="US_OPEN"
    assert classify_market_session(datetime(2026,1,20,9,30,tzinfo=ZoneInfo("America/New_York")),policies)=="US_OPEN"
