from __future__ import annotations

import argparse

from finam_core.analytics.exit_policy_selector import ExitPolicySelector


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--min-profit-factor", type=float, default=1.2)
    parser.add_argument("--max-allowed-drawdown", type=float, default=-999999.0)
    parser.add_argument("--migrate", action="store_true")

    args = parser.parse_args()

    selector = ExitPolicySelector()

    if args.migrate:
        selector.migrate_selected_policy()

    selected = selector.select_best_policy(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        min_profit_factor=args.min_profit_factor,
        max_allowed_drawdown=args.max_allowed_drawdown,
    )

    if selected is None:
        print(
            "EXIT_POLICY_SELECTED_EMPTY "
            f"symbol={args.symbol} "
            f"strategy={args.strategy} "
            f"timeframe={args.timeframe}",
            flush=True,
        )
        return 0

    selector.save_selected_policy(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        selected=selected,
    )

    print(
        "EXIT_POLICY_SELECTED_OK "
        f"symbol={args.symbol} "
        f"strategy={args.strategy} "
        f"timeframe={args.timeframe} "
        f"policy={selected['selected_policy']} "
        f"take={selected['take_distance']} "
        f"stop={selected['stop_distance']} "
        f"pf={selected['profit_factor']} "
        f"net_pnl={selected['net_pnl']} "
        f"max_dd={selected['max_drawdown']}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
