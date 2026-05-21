from __future__ import annotations

import argparse

from finam_core.analytics.exit_policy_repository import (
    ExitPolicySimulationRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--migrate", action="store_true")

    args = parser.parse_args()

    repo = ExitPolicySimulationRepository()

    if args.migrate:
        repo.migrate_exit_policy_simulation()

    results = repo.build_simulation(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
    )

    repo.save_simulation_results(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        results=results,
    )

    if results:
        best = sorted(
            results,
            key=lambda x: (
                x.simulated_profit_factor,
                x.simulated_net_pnl,
                -abs(x.simulated_max_drawdown),
            ),
            reverse=True,
        )[0]

        print(
            "ANALYTICS_EXIT_POLICY_SIMULATION_OK "
            f"symbol={args.symbol} "
            f"strategy={args.strategy} "
            f"timeframe={args.timeframe} "
            f"policies={len(results)} "
            f"best_policy={best.policy_name} "
            f"best_pf={best.simulated_profit_factor} "
            f"best_net_pnl={best.simulated_net_pnl} "
            f"best_max_dd={best.simulated_max_drawdown}",
            flush=True,
        )
    else:
        print(
            "ANALYTICS_EXIT_POLICY_SIMULATION_EMPTY "
            f"symbol={args.symbol} "
            f"strategy={args.strategy} "
            f"timeframe={args.timeframe}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
