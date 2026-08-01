from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


PATH=Path("src/scripts/run_autonomous_instrument_scout_v1.py")


def module():
    spec=spec_from_file_location("tradable_volatility_scout",PATH)
    result=module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(result)
    return result


def bars(count=140, *, step=0.001, volume=1000.0):
    result=[]; price=100.0
    for index in range(count):
        direction=1 if index%3 else -1
        change=step*direction*(1+index/count)
        close=price*(1+change)
        result.append({"close":close,"high":max(price,close)*1.0008,
                       "low":min(price,close)*.9992,"volume":volume*(1+index/count)})
        price=close
    return result


def test_features_are_scale_free_and_causal() -> None:
    scout=module()
    first=scout.volatility_features(bars())
    scaled=[{**item,"close":item["close"]*10,"high":item["high"]*10,"low":item["low"]*10}
            for item in bars()]
    second=scout.volatility_features(scaled)
    assert abs(first["atr_pct"]-second["atr_pct"])<1e-9
    assert 0<=first["atr_percentile"]<=100
    assert 0<=first["directional_efficiency"]<=1
    assert 0<=first["zero_volume_share"]<=1


def test_bad_execution_reduces_score() -> None:
    scout=module(); features=scout.volatility_features(bars())
    good=scout.tradable_volatility_score({**features,"spread_atr_ratio":.05})
    bad=scout.tradable_volatility_score({**features,"spread_atr_ratio":.90,
                                        "zero_volume_share":.50})
    assert good>bad
