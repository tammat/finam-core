from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--batch-id", default="")
    p.add_argument("--campaigns", type=int, default=3)
    p.add_argument("--symbols", required=True)
    p.add_argument("--timeframes", default="M5")
    p.add_argument("--strategies", default="BR_CONSERVATIVE_BREAKOUT")
    p.add_argument("--run-secs", type=float, default=60.0)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    batch_id = args.batch_id or "batch-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    failed = 0

    print(f"REPLAY_BATCH_START batch_id={batch_id} campaigns={args.campaigns}", flush=True)

    for i in range(1, args.campaigns + 1):
        campaign_id = f"{batch_id}-{i:04d}"

        cmd = [
            sys.executable,
            "src/scripts/run_replay_campaign.py",
            "--symbols", args.symbols,
            "--timeframes", args.timeframes,
            "--strategies", args.strategies,
            "--campaign-id", campaign_id,
            "--run-secs", str(args.run_secs),
        ]

        if args.dry_run:
            cmd.append("--dry-run")

        print(f"REPLAY_BATCH_CAMPAIGN campaign_id={campaign_id} cmd={' '.join(cmd)}", flush=True)

        result = subprocess.run(cmd)
        if result.returncode != 0:
            failed += 1

    print(f"REPLAY_BATCH_DONE batch_id={batch_id} failed={failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
