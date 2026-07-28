import json
import os

from finam_core.analytics.runtime_guard_config_loader_v1 import (
    RuntimeGuardConfigLoaderV1,
)
from finam_core.runtime.research_contract_key_v1 import (
    normalize_research_contract_key_v1,
)


def test_ng_live_timeframe_is_normalized_to_m1():
    key = normalize_research_contract_key_v1(
        symbol="NGQ6@RTSX",
        strategy="NG_CONSERVATIVE_BREAKOUT_M1",
        timeframe="LIVE",
        side="LONG",
        session_name="morning",
        regime="trend_up",
    )

    assert key.normalized_symbol == "NG_CONT"
    assert key.strategy == "NG_CONSERVATIVE_BREAKOUT_M1"
    assert key.timeframe == "M1"


def test_equity_live_timeframe_is_normalized_to_m5():
    key = normalize_research_contract_key_v1(
        symbol="SBER@MISX",
        strategy="VOLATILITY_BREAKOUT_EQUITY",
        timeframe="LIVE",
        side="LONG",
        session_name="morning",
        regime="trend_up",
    )

    assert key.normalized_symbol == "SBER@MISX"
    assert key.strategy == "VOLATILITY_BREAKOUT_EQUITY"
    assert key.timeframe == "M5"


def test_equity_mean_reversion_live_timeframe_is_normalized_to_m5():
    key = normalize_research_contract_key_v1(
        symbol="NVTK@MISX",
        strategy="MEAN_REVERSION_EQUITY",
        timeframe="LIVE",
        side="LONG",
        session_name="main",
        regime="range",
    )

    assert key.strategy == "MEAN_REVERSION_EQUITY"
    assert key.timeframe == "M5"


def test_runtime_guard_lookup_normalizes_active_br_contract_and_live_timeframe(tmp_path):
    path = tmp_path / "guard.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "symbol": "BRN6@RTSX",
                        "strategy": "BR_CONSERVATIVE_BREAKOUT",
                        "timeframe": None,
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


def test_runtime_guard_uses_safe_unknown_dimension_fallback(tmp_path):
    path = tmp_path / "guard.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "symbol": "BRM6@RTSX",
                        "strategy": "BR_CONSERVATIVE_BREAKOUT",
                        "timeframe": "M5",
                        "regime": "UNKNOWN",
                        "volatility_regime": "UNKNOWN",
                        "session_type": "UNKNOWN",
                        "guard_decision": "WATCH",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    loader = RuntimeGuardConfigLoaderV1(path)

    assert (
        loader.decision(
            symbol="BRQ6@RTSX",
            strategy="BR_CONSERVATIVE_BREAKOUT",
            timeframe="LIVE",
            regime="TREND_UP_HIGH_VOL",
            volatility_regime="HIGH",
            session_type="EUROPE_OVERLAP",
        )
        == "WATCH"
    )


def test_runtime_guard_fallback_chooses_most_restrictive_decision(tmp_path):
    path = tmp_path / "guard.json"
    path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "symbol": "BRQ6@RTSX",
                        "strategy": "BR_CONSERVATIVE_BREAKOUT",
                        "timeframe": "M5",
                        "regime": "UNKNOWN",
                        "volatility_regime": "UNKNOWN",
                        "session_type": "UNKNOWN",
                        "guard_decision": "ALLOW",
                    },
                    {
                        "symbol": "BRQ6@RTSX",
                        "strategy": "BR_CONSERVATIVE_BREAKOUT",
                        "timeframe": "M5",
                        "regime": "TREND_UP_HIGH_VOL",
                        "volatility_regime": "UNKNOWN",
                        "session_type": "UNKNOWN",
                        "guard_decision": "BLOCK",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    loader = RuntimeGuardConfigLoaderV1(path)

    assert (
        loader.decision(
            symbol="BRQ6@RTSX",
            strategy="BR_CONSERVATIVE_BREAKOUT",
            timeframe="LIVE",
            regime="TREND_UP_HIGH_VOL",
            volatility_regime="HIGH",
            session_type="EUROPE_OVERLAP",
        )
        == "BLOCK"
    )


def test_runtime_guard_reloads_changed_snapshot(tmp_path):
    path = tmp_path / "guard.json"
    item = {
        "symbol": "BRQ6@RTSX",
        "strategy": "BR_CONSERVATIVE_BREAKOUT",
        "timeframe": "M5",
        "regime": "UNKNOWN",
        "volatility_regime": "UNKNOWN",
        "session_type": "UNKNOWN",
        "guard_decision": "WATCH",
    }
    path.write_text(json.dumps({"items": [item]}), encoding="utf-8")

    loader = RuntimeGuardConfigLoaderV1(path)
    assert (
        loader.decision(
            symbol="BRQ6@RTSX",
            strategy="BR_CONSERVATIVE_BREAKOUT",
            timeframe="LIVE",
        )
        == "WATCH"
    )

    item["guard_decision"] = "BLOCK"
    path.write_text(json.dumps({"items": [item]}), encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    assert (
        loader.decision(
            symbol="BRQ6@RTSX",
            strategy="BR_CONSERVATIVE_BREAKOUT",
            timeframe="LIVE",
        )
        == "BLOCK"
    )
