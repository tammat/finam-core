from datetime import datetime, timezone
from pathlib import Path

from finam_core.research.purged_split import label_horizon_bars, purged_bar_window


class Bar:
    def __init__(self, no: int) -> None:
        self.ts = datetime(2026,1,1,0,no,tzinfo=timezone.utc)


def test_dynamic_exit_uses_maximum_label_horizon() -> None:
    assert label_horizon_bars({"hold":5,"exit_policy_code":"DYNAMIC_EXIT_V1","exit_max_holding_bars":20}) == 20


def test_bar_window_embargoes_start_by_label_horizon() -> None:
    bars = [Bar(no) for no in range(50)]
    start, end, embargo = purged_bar_window(bars,start=10,end=40,parameters={"hold":5})
    assert (start,end,embargo) == (bars[15].ts,bars[39].ts,5)


def test_active_research_engines_use_purged_boundaries() -> None:
    root = Path("src/scripts")
    for name in (
        "run_strategy_hypothesis_execution_pipeline_v2.py",
        "build_edge_hypothesis_discovery_v1.py",
        "build_edge_regime_hypothesis_discovery_v2.py",
        "build_session_execution_edge_v1.py",
        "build_momentum_edge_oos_rank_v1.py",
        "validate_momentum_edge_oos_v1.py",
    ):
        source = (root/name).read_text()
        assert "purged_bar_window" in source
        assert "trades_in_purged_window" in source

    assert "label_horizon_bars" in (root/"backtest_runner.py").read_text()


def test_auxiliary_engines_apply_horizon_embargo() -> None:
    root = Path("src/scripts")
    for name in ("run_relative_strength_parameter_adapter_v2.py","run_intermarket_lead_lag_parameter_adapter_v2.py"):
        assert "embargo" in (root/name).read_text()
    for name in ("build_relationship_factory_v2.py","build_intermarket_lead_lag_engine_v1.py"):
        source = (root/name).read_text()
        assert "validation_end + lag" in source
    swing = (root/"run_swing_selection_validation_engine_v1.py").read_text()
    assert "label_horizon_bars" in swing
    assert "selection_i-horizon" in swing
    assert "validation_i-horizon" in swing
