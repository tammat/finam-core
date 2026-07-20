from pathlib import Path

from scripts.run_checkpointed_walkforward_v4 import _finalize_results, _one_sided_sign_p_value


def test_worker_is_fold_checkpointed_and_early_prunes() -> None:
    source=Path("src/scripts/run_checkpointed_walkforward_v4.py").read_text()
    assert "walkforward_fold_checkpoint_v4" in source
    assert "RECOVERED_AFTER_STOP" in source
    assert "EARLY_INSUFFICIENT_TRADES" in source
    assert "EARLY_NEGATIVE_EXPECTANCY" in source
    assert "COARSE_NOT_TOP_10_PERCENT" in source
    assert "rank_pct<=.10" in source
    assert "cpu_limit={CPU_LIMIT}" in source
    assert "attempts=attempts+1" in source
    assert "variants_complete" in source
    assert "def _select_clean_holdout" in source
    assert "NOT_SELECTED_FOR_CLEAN_HOLDOUT" in source
    assert "generate_series(3,4)" in source
    assert "SELECT variant_task_id,5" in source
    assert "def _enqueue_remediation_variants" in source
    assert "oos_remediation_candidate_v1" in source
    assert "adaptive_scenario_id" in source
    assert "def _reconcile_remediation_results" in source
    assert "COARSE_SEARCH_REJECTED" in source
    assert "remediation_variants_inserted" in source
    assert "confirmation_after_ts" in source
    assert "FUTURE_ONLY_COHORT_TOO_SHORT" in source
    assert "t.exit_ts<=end_ts" in source


def test_autonomous_cycle_uses_checkpointed_worker() -> None:
    source=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    assert '"WALKFORWARD": "src/scripts/run_checkpointed_walkforward_v4.py"' in source
    assert 'step.endswith("run_checkpointed_walkforward_v4.py")' in source


def test_sign_test_and_result_insert_are_well_formed() -> None:
    assert _one_sided_sign_p_value([]) == 1.0
    assert _one_sided_sign_p_value([1.0, 2.0, 3.0]) == 0.125

    class Cursor:
        rowcount = 1
        selected = False

        def execute(self, query, args=()):
            if query.lstrip().startswith("SELECT v.*"):
                self.selected = True
            if query.lstrip().startswith("INSERT INTO analytics.walkforward_edge_search_v3"):
                assert query.count("%s") == len(args)

        def fetchall(self):
            metric = {
                "net_pnls": [2.0] * 30,
                "gross_pnls": [3.0] * 30,
                "max_drawdown": 0,
                "start": "2026-01-01T00:00:00+00:00",
                "end": "2026-01-02T00:00:00+00:00",
                "average_fill_ratio": 1,
                "fallback_quote_share": 0,
                "microstructure_coverage": 1,
                "signal_latency_bars": 1,
                "capacity_rub": 1_000_000,
                "contract_spec_coverage": 1,
                "daily_pnl": [{"date": "2026-01-02", "pnl": 60}],
            }
            gate = {
                "fold_min_trades": 1,
                "fold_min_profit_factor": 1,
                "fold_min_expectancy": 0,
                "min_trades": 1,
                "min_profit_factor": 1,
                "min_expectancy": 0,
                "min_folds_passed": 3,
                "final_holdout_required": True,
            }
            return [{
                "variant_task_id": "00000000-0000-0000-0000-000000000001",
                "algorithm_code": "EMA_TREND",
                "strategy_code": "EMA_TREND",
                "symbol": "SBER@MISX",
                "timeframe": "M5",
                "parameter_json": {"lookback": 20},
                "gate_policy": {"walkforward": gate},
                "fold_data": {str(index): metric for index in range(6)},
            }]

    assert _finalize_results(Cursor(), "00000000-0000-0000-0000-000000000002") == 1
