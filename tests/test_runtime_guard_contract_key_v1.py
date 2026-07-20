import json

from finam_core.analytics.runtime_guard_config_loader_v1 import (
    RuntimeGuardConfigLoaderV1,
)


def test_runtime_guard_lookup_normalizes_active_br_contract_and_live_timeframe(tmp_path):
    path = tmp_path / "guard.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "symbol": "BRN6@RTSX",
                        "strategy": "BR_CONSERVATIVE_BREAKOUT",
                        "timeframe": "M5",
                        "regime": "TREND_UP_HIGH_VOL",
                        "volatility_regime": "UNKNOWN",
                        "session_type": "EUROPE_OVERLAP",
                        "guard_decision": "INSUFFICIENT_DATA",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    loader = RuntimeGuardConfigLoaderV1(path)
    loader.load()

    result = loader.lookup(
        symbol="BRQ6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="LIVE",
        regime="trend_up_high_vol",
        volatility_regime="UNKNOWN",
        session_type="EUROPE_OVERLAP",
    )

    assert result is not None
    assert result["guard_decision"] == "INSUFFICIENT_DATA"
