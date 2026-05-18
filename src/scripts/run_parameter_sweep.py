from __future__ import annotations

import argparse
import itertools
import subprocess
import sys


def parse_float_list(value: str) -> list[float]:
    return [float(x.strip()) for x in value.split(",") if x.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--sweep-id", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--timeframes", default="D1")
    p.add_argument("--strategy", default="MOEX_SIMPLE_MOMENTUM")
    p.add_argument("--date-from", required=True)
    p.add_argument("--date-to", required=True)
    p.add_argument("--stop-pcts", default="0.005,0.01,0.015,0.02")
    p.add_argument("--take-pcts", default="0.01,0.02,0.03,0.04")
    p.add_argument("--holding-bars", default="1,3,5")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    stop_pcts = parse_float_list(args.stop_pcts)
    take_pcts = parse_float_list(args.take_pcts)
    holding_bars_list = parse_int_list(args.holding_bars)

    combos = list(itertools.product(stop_pcts, take_pcts, holding_bars_list))

    print(
        f"PARAM_SWEEP_START sweep_id={args.sweep_id} combos={len(combos)}",
        flush=True,
    )

    failed = 0

    for idx, (stop_pct, take_pct, holding_bars) in enumerate(combos, start=1):
        campaign_id = (
            f"{args.sweep_id}-"
            f"s{str(stop_pct).replace('.', 'p')}-"
            f"t{str(take_pct).replace('.', 'p')}-"
            f"h{holding_bars}"
        )

        cmd = [
            sys.executable,
            "src/scripts/run_replay_campaign.py",
            "--symbols", args.symbols,
            "--timeframes", args.timeframes,
            "--strategies", args.strategy,
            "--data-source", "moex",
            "--date-from", args.date_from,
            "--date-to", args.date_to,
            "--campaign-id", campaign_id,
            "--stop-pct", str(stop_pct),
            "--take-pct", str(take_pct),
            "--holding-bars", str(holding_bars),
        ]

        # Русский комментарий: параметры пока передаём через env-compatible argv в external pipeline на следующем шаге.
        # На этом шаге фиксируем sweep orchestration.
        print(
            "PARAM_SWEEP_RUN "
            f"sweep_id={args.sweep_id} index={idx} campaign_id={campaign_id} "
            f"stop_pct={stop_pct} take_pct={take_pct} holding_bars={holding_bars} "
            f"cmd={' '.join(cmd)}",
            flush=True,
        )

        if args.dry_run:
            continue

        env = None
        result = subprocess.run(cmd, env=env)

        if result.returncode != 0:
            failed += 1
            print(
                f"PARAM_SWEEP_FAILED campaign_id={campaign_id} code={result.returncode}",
                flush=True,
            )

    print(
        f"PARAM_SWEEP_DONE sweep_id={args.sweep_id} combos={len(combos)} failed={failed}",
        flush=True,
    )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
