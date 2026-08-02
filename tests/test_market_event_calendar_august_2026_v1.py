from pathlib import Path


def test_august_events_are_source_backed_and_non_directional() -> None:
    sql = Path("sql/analytics/268_market_event_calendar_august_2026_v1.sql").read_text()
    for event in (
        "OPEC_PLUS_2026_08_02_AWAITING",
        "EIA_OIL_2026_08_05",
        "EIA_GAS_2026_08_06",
        "CHINA_CPI_2026_08_09",
        "CHINA_PMI_2026_08_31",
        "CBR_RATE_2026_09_11",
    ):
        assert event in sql
    for source in ("opec.org", "eia.gov", "stats.gov.cn", "cbr.ru"):
        assert source in sql
    assert sql.count('"directional_signal":false') == 5
    assert "ON CONFLICT(event_code) DO UPDATE" in sql


def test_event_windows_are_instrument_scoped() -> None:
    sql = Path("sql/analytics/268_market_event_calendar_august_2026_v1.sql").read_text()
    assert "ARRAY['BRQ6@RTSX']" in sql
    assert "ARRAY['NGQ6@RTSX']" in sql
    assert "ARRAY['SBER@MISX','CNYRUBF@RTSX','USDRUBF@RTSX']" in sql
    assert "ARRAY['*']" not in sql
