from decimal import Decimal
from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src/scripts/build_v5_hierarchical_evidence_v1.py"
SPEC = importlib.util.spec_from_file_location("v5_hierarchy", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def stats(trades, net, wins, losses, move=100, cost=10):
    return MODULE.EvidenceStats(trades, Decimal(net), Decimal(wins), Decimal(losses),
                                Decimal(move), Decimal(cost))


def test_hierarchy_never_promotes_non_exact_level() -> None:
    decision, reason, _, _ = MODULE.classify(
        stats(100,"20","30","10"), exact=False
    )
    assert decision == "COLLECT"
    assert reason == "V5_HIERARCHY_SUPPORTS_EXACT_VALIDATION_ONLY"


def test_exact_level_requires_cost_adjusted_observable_edge() -> None:
    decision, reason, pf, observable = MODULE.classify(
        stats(80,"20","30","10",move=100,cost=10), exact=True
    )
    assert (decision, reason) == ("READY_FOR_OOS", "V5_EXACT_CONTEXT_COST_ADJUSTED_EDGE")
    assert pf == Decimal("3") and observable


def test_small_sample_is_discovery_not_pass() -> None:
    assert MODULE.classify(stats(9,"2","3","1"), exact=True)[0] == "DISCOVERY_ONLY"


def test_persistent_negative_instrument_can_stop_after_twenty() -> None:
    decision, reason, _, _ = MODULE.classify(stats(20,"-8","2","10"), exact=False)
    assert (decision, reason) == ("EARLY_STOP", "V5_PERSISTENT_NEGATIVE_EXPECTANCY")


def test_exact_collection_priority_favors_existing_evidence() -> None:
    score_1 = MODULE.evidence_priority_score(
        stats(1,"0","0","0"), decision="DISCOVERY_ONLY", exact=True
    )
    score_5 = MODULE.evidence_priority_score(
        stats(5,"0","0","0"), decision="DISCOVERY_ONLY", exact=True
    )
    score_10 = MODULE.evidence_priority_score(
        stats(10,"0","0","0"), decision="DISCOVERY_ONLY", exact=True
    )
    score_20 = MODULE.evidence_priority_score(
        stats(20,"1","2","1"), decision="COLLECT", exact=True
    )
    assert score_20 > score_10 > score_5 > score_1


def test_supporting_level_never_outranks_exact_branch() -> None:
    supporting = MODULE.evidence_priority_score(
        stats(80,"20","30","10"), decision="COLLECT", exact=False
    )
    exact = MODULE.evidence_priority_score(
        stats(1,"0","0","0"), decision="DISCOVERY_ONLY", exact=True
    )
    assert exact > supporting


def test_early_stop_is_removed_from_collection_priority() -> None:
    stopped = MODULE.evidence_priority_score(
        stats(20,"-8","2","10"), decision="EARLY_STOP", exact=True
    )
    assert stopped < 0


def test_scope_and_timeframe_are_physical_dimensions() -> None:
    migration = (ROOT / "sql/analytics/215_v5_hierarchical_evidence_router_v1.sql").read_text()
    assert "scope_code" in migration and "timeframe_code" in migration
    source = PATH.read_text()
    assert "closed_trades_fresh_v5_confirmed" in source
    assert "FRESH_V5_CONFIRM" in source
    assert "FRESH_V3" not in source and "FRESH_V4" not in source


def test_scheduler_allowlists_the_implemented_router() -> None:
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"HIERARCHICAL_EVIDENCE_ROUTER_V1": "src/scripts/build_v5_hierarchical_evidence_v1.py"' in scheduler


def test_evidence_timeframe_rejects_live_transport_marker() -> None:
    assert MODULE.evidence_timeframe("BRQ6@RTSX", "LIVE", "M5") == "M1"
    assert MODULE.evidence_timeframe("NGQ6@RTSX", "LIVE", "M5") == "M1"
    assert MODULE.evidence_timeframe("SBER@MISX", "LIVE", "M5") == "M5"
    assert MODULE.evidence_timeframe("UNKNOWN", "LIVE", "") == "UNKNOWN"


def test_r_metrics_use_net_pnl_over_initial_stop_risk() -> None:
    sample = stats(0, "0", "0", "0", move=0, cost=0)
    sample.add(
        net_pnl=Decimal("15"), gross_pnl=Decimal("20"),
        commission=Decimal("5"), realized_r=Decimal("0.5"),
    )
    sample.add(
        net_pnl=Decimal("-5"), gross_pnl=Decimal("-3"),
        commission=Decimal("2"), realized_r=Decimal("-0.25"),
    )
    assert sample.net_pnl_r == Decimal("0.25")
    assert sample.net_pnl_r / sample.r_observations == Decimal("0.125")


def test_router_persists_r_metrics_from_entry_stop() -> None:
    source = PATH.read_text()
    assert "entry_stop_price" in source
    assert "net_pnl_r,expectancy_r,r_observable" in source
