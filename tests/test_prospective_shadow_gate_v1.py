from datetime import datetime, timedelta, timezone
from decimal import Decimal

from scripts.run_prospective_shadow_gate_v1 import decide, independent
from pathlib import Path


def test_non_overlapping_observations_only():
    start = datetime(2026, 8, 3, tzinfo=timezone.utc)
    rows = [
        {"source_signal_id": 1, "label_start_ts": start, "label_end_ts": start + timedelta(hours=1)},
        {"source_signal_id": 2, "label_start_ts": start + timedelta(minutes=5), "label_end_ts": start + timedelta(hours=1)},
        {"source_signal_id": 3, "label_start_ts": start + timedelta(hours=1), "label_end_ts": start + timedelta(hours=2)},
    ]
    assert [row["source_signal_id"] for row in independent(rows)] == [1, 3]


def test_gate_accumulates_before_eight():
    assert decide({"n": 7, "expectancy": Decimal("1"), "pf": Decimal("2"), "days": 3,
                   "top_gain_share": Decimal("0.2")})[0] == "ACCUMULATING"


def test_gate_rejects_clear_early_loss():
    assert decide({"n": 8, "expectancy": Decimal("-0.3"), "pf": Decimal("0.5"), "days": 2,
                   "top_gain_share": Decimal("0.4")})[0] == "EARLY_REJECT"


def test_gate_requires_diversified_positive_ten():
    value = {"n": 10, "expectancy": Decimal("0.2"), "pf": Decimal("1.3"), "days": 2,
             "top_gain_share": Decimal("0.5")}
    assert decide(value)[0] == "READY_FOR_V5"
    value["top_gain_share"] = Decimal("0.8")
    assert decide(value)[0] == "ACCUMULATING"


def test_gate_runs_before_v5_worker_in_control_chain():
    source = Path("src/scripts/run_entry_exit_control_chain_v1.py").read_text()
    assert source.index("run_prospective_shadow_gate_v1.py") < source.index("run_v5_purged_oos_worker_v1.py")


def test_prospective_gate_is_diagnostic_only_and_cannot_reset_v5():
    source = Path("src/scripts/run_prospective_shadow_gate_v1.py").read_text()
    assert "gate_mode=DIAGNOSTIC_ONLY" in source
    run_body = source[source.index("def run("):source.index("def main(")]
    assert "UPDATE analytics.trade_outcome_oos_admission_v1" not in run_body
    assert "UPDATE analytics.v5_oos_run_v1" not in run_body
    assert "UPDATE analytics.v5_post_fix_branch_registry_v1" not in run_body


def test_control_center_exposes_branch_funnel_and_gate():
    source = Path("src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py").read_text()
    assert "Диагностика Shadow и прямой V5" in source
    assert "prospective_shadow_gate_latest_v1" in source
    assert "independent_closed" in source
    assert "v5_observations" in source
    assert "Она не останавливает V5" in source
