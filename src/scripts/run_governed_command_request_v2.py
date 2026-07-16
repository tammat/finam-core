from __future__ import annotations

import argparse

from marketcore.action.command_worker_v2 import GovernedCommandWorkerV2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()
    status = GovernedCommandWorkerV2().run_once(request_id=args.request_id)
    print(f"request_status={status or 'NOT_FOUND'}", flush=True)
    return 0 if status == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
