from src.scripts.build_swing_hypothesis_factory_v1 import balanced_candidate_cap
from src.scripts.generate_next_swing_research_plan_v1 import diverse_plan_candidates


def test_factory_cap_rotates_across_symbols_inside_family_and_timeframe():
    rows = [
        ("MOMENTUM", "ENGINE", symbol, "D1", {"variant": variant})
        for symbol in ("BR_ROLLING@RTSX", "GAZP@MISX", "SBER@MISX")
        for variant in range(10)
    ]
    selected = balanced_candidate_cap(rows, 6)
    assert {row[2] for row in selected} == {
        "BR_ROLLING@RTSX", "GAZP@MISX", "SBER@MISX"
    }
    assert len(selected) == 6


def test_next_plan_does_not_allow_one_market_to_fill_all_slots():
    rows = (
        [{"symbol": "BR_ROLLING@RTSX", "rank": rank} for rank in range(20)]
        + [{"symbol": "SBER@MISX", "rank": 21}]
        + [{"symbol": "GAZP@MISX", "rank": 22}]
    )
    selected = diverse_plan_candidates(rows, 12)
    assert len(selected) == 12
    assert "SBER@MISX" in {row["symbol"] for row in selected}
    assert "GAZP@MISX" in {row["symbol"] for row in selected}
