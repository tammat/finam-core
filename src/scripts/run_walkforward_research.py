from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date

from finam_core.research.walkforward_engine import WalkForwardEngine


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--research-id", required=True)
    p.add_argument("--symbols", required=True)
    p.add_argument("--timeframes", default="D1")
    p.add_argument("--strategies", default="MOEX_SIMPLE_MOMENTUM")
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)
    p.add_argument("--train-months", type=int, default=6)
    p.add_argument("--test-months", type=int, default=1)
    p.add_argument("--step-months", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    windows = WalkForwardEngine().build_windows(
        start_date=date.fromisoformat(args.start_date),
        end_date=date.fromisoformat(args.end_date),
        train_months=args.train_months,
        test_months=args.test_months,
        step_months=args.step_months,
    )

    print(
        f"WALKFORWARD_START research_id={args.research_id} windows={len(windows)}",
        flush=True,
    )

    failed = 0

    for w in windows:
        campaign_id = f"{args.research_id}-wf{w.index:04d}"

        cmd = [
            sys.executable,
            "src/scripts/run_replay_campaign.py",
            "--symbols", args.symbols,
            "--timeframes", args.timeframes,
            "--strategies", args.strategies,
            "--data-source", "moex",
            "--date-from", w.test_from.isoformat(),
            "--date-to", w.test_to.isoformat(),
            "--campaign-id", campaign_id,
        ]

        if args.dry_run:
            cmd.append("--dry-run")

        print(
            "WALKFORWARD_WINDOW "
            f"research_id={args.research_id} "
            f"window={w.index} "
            f"train={w.train_from}:{w.train_to} "
            f"test={w.test_from}:{w.test_to} "
            f"campaign_id={campaign_id}",
            flush=True,
        )

        result = subprocess.run(cmd)

        if result.returncode != 0:
            failed += 1
            print(
                f"WALKFORWARD_WINDOW_FAILED campaign_id={campaign_id} code={result.returncode}",
                flush=True,
            )

    print(
        f"WALKFORWARD_DONE research_id={args.research_id} windows={len(windows)} failed={failed}",
        flush=True,
    )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
