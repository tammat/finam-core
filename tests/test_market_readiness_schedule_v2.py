from pathlib import Path


def test_market_readiness_covers_the_full_configured_sessions() -> None:
    migration = Path(
        "sql/analytics/167_market_readiness_and_remediation_dispatch_v1.sql"
    ).read_text(encoding="utf-8")
    assert "MARKET_OPEN_READINESS_V2_TIMEFRAME_AWARE" in migration
    assert "time '23:55'" in migration
    assert "time '19:15'" in migration
    assert "interval_minutes=5" in migration
