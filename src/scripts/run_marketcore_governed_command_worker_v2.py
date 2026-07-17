from __future__ import annotations

import argparse

from marketcore.action.command_worker_v2 import COMMANDS, GovernedCommandWorkerV2


def scheduled_request_kinds(request_kind: str | None) -> tuple[str | None, ...]:
    """The installed research timer also owns governed edge-search requests."""
    if request_kind == "RESEARCH_REFRESH":
        return ("EDGE_SEARCH_RUN", "RESEARCH_REFRESH")
    return (request_kind,)


def main() -> int:
    parser = argparse.ArgumentParser(description="Process governed Research/Paper command requests")
    parser.add_argument("--request-id")
    parser.add_argument("--request-kind", choices=tuple(COMMANDS))
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    if args.limit < 1 or args.limit > 20:
        parser.error("--limit must be between 1 and 20")
    if args.request_id and args.limit != 1:
        parser.error("--request-id requires --limit=1")

    worker = GovernedCommandWorkerV2()
    processed = 0
    statuses: list[str] = []
    for _ in range(args.limit):
        status = None
        for request_kind in scheduled_request_kinds(args.request_kind):
            status = worker.run_once(request_id=args.request_id, request_kind=request_kind)
            if status is not None:
                break
        if status is None:
            break
        processed += 1
        statuses.append(status)
    print(f"processed={processed}")
    print(f"statuses={','.join(statuses) or 'NONE'}")
    print("VERDICT=MARKETCORE_GOVERNED_COMMAND_WORKER_V2_OK")
    return 2 if "FAILED" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
