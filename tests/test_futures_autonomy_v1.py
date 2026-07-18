from datetime import date,timedelta
from pathlib import Path

from scripts.build_futures_roll_decision_v1 import choose_contract


ROOT=Path(__file__).resolve().parents[1]
POLICY={"roll_days_before_expiry":5,"next_volume_ratio":1.0}


def row(symbol,days,volume):
    return {"symbol":symbol,"expiration_date":date.today()+timedelta(days=days),
            "days_to_expiry":days,"median_volume":volume,"bars":7000}


def test_keeps_liquid_front_contract_before_roll_window():
    current,selected,reason=choose_contract([row("BRQ6@RTSX",16,315),row("BRU6@RTSX",44,25)],POLICY)
    assert current["symbol"] == selected["symbol"] == "BRQ6@RTSX"
    assert reason == "KEEP_LIQUID_FRONT"


def test_rolls_in_expiry_window_or_on_liquidity_crossover():
    assert choose_contract([row("NGN6@RTSX",5,415),row("NGQ6@RTSX",40,35)],POLICY)[1]["symbol"] == "NGQ6@RTSX"
    assert choose_contract([row("BRQ6@RTSX",16,100),row("BRU6@RTSX",44,120)],POLICY)[2] == "LIQUIDITY_CROSSOVER_ROLL"


def test_autonomous_cycle_and_db_policy_own_roll_decision():
    migration=(ROOT/"sql/analytics/097_autonomous_futures_leverage_roll_v1.sql").read_text()
    cycle=(ROOT/"src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    selector=(ROOT/"src/scripts/edge_research_universe_v1.py").read_text()
    assert "futures_autonomy_policy_v1" in migration
    assert "futures_roll_decision_v1" in migration
    assert "RESOLVE_FUTURES_ROLL" in migration and "RESOLVE_FUTURES_ROLL" in cycle
    assert "ROLLOVER_CONTRACT_NOT_SELECTED" in selector
