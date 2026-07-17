from marketcore.action.command_worker_v2 import GovernedCommandWorkerV2


def main() -> int:
    status = GovernedCommandWorkerV2().run_once(request_kind="EDGE_SEARCH_RUN")
    print(f"request_status={status or 'NO_PENDING_REQUEST'}")
    print("VERDICT=EDGE_SEARCH_COMMAND_QUEUE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
