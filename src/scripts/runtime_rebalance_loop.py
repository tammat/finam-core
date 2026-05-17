from __future__ import annotations

import os
import sys
import subprocess


def run(cmd: list[str]) -> None:
    print("RUNTIME_REBALANCE_RUN " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    python_bin = os.getenv("PYTHON_BIN") or sys.executable
    env = os.environ.copy()
    env["PYTHONPATH"] = env.get("PYTHONPATH", "src")

    steps = [
        [python_bin, "src/scripts/aggregate_continuous_smart_money.py"],
        [python_bin, "src/scripts/classify_institutional_flow_regime.py"],
        [python_bin, "src/scripts/select_cross_contract_liquidity.py"],
        [python_bin, "src/scripts/update_market_opportunity_metrics.py"],
        [python_bin, "src/scripts/update_moex_top_universe_from_volatility_scan.py"],
        [python_bin, "src/scripts/update_market_opportunity_metrics_from_moex_top.py"],
        [python_bin, "src/scripts/update_market_opportunity_scores_v2.py"],
        [python_bin, "src/scripts/update_dynamic_watchlist_from_opportunities.py"],
        [python_bin, "src/scripts/update_market_event_calendar.py"],
        [python_bin, "src/scripts/send_market_event_calendar_alerts_telegram.py"],
    ]

    for cmd in steps:
        subprocess.run(cmd, env=env, check=True)

    print("OK: runtime rebalance loop completed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
