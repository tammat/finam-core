#!/usr/bin/env bash
set -euo pipefail

grep -q "CREATE TABLE IF NOT EXISTS strategy_walkforward_results" scripts/migrate_strategy_walkforward_results_v1.sh
grep -q "train_pf" scripts/migrate_strategy_walkforward_results_v1.sh
grep -q "test_pf" scripts/migrate_strategy_walkforward_results_v1.sh
grep -q "degradation_score" scripts/migrate_strategy_walkforward_results_v1.sh
grep -q "stability_score" scripts/migrate_strategy_walkforward_results_v1.sh

echo "STRATEGY_WALKFORWARD_RESULTS_TABLE_TEST_OK"
