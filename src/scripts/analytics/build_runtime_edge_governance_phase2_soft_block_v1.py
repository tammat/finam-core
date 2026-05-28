from __future__ import annotations

import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.execution.runtime_edge_governance_soft_block_v1 import (
    RuntimeEdgeGovernanceSoftBlockV1,
)


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def main() -> int:
    governance = RuntimeEdgeGovernanceSoftBlockV1()

    cases = [
        ("BR_ROLLING@RTSX", "BUY", 8),
        ("BR_ROLLING@RTSX", "BUY", 19),
    ]

    decisions = []

    print("RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK_V1", flush=True)

    for symbol, side, hour in cases:
        decision = governance.decide(
            symbol=symbol,
            side=side,
            ts=datetime(2026, 5, 28, hour, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        )
        decisions.append(decision)

        print(
            "RUNTIME_EDGE_GOVERNANCE_PHASE2_ROW",
            f"symbol={decision.symbol}",
            f"side={decision.side}",
            f"hour_msk={decision.hour_msk}",
            f"allowed={decision.allowed}",
            f"action={decision.action}",
            f"reason={decision.reason}",
            f"session_action={decision.session_action}",
            f"strict_reason={decision.strict_reason}",
            f"decay_state={decision.decay_state}",
            f"expectancy_points={decision.expectancy_points}",
            f"closed_trades={decision.closed_trades}",
            flush=True,
        )

    allowed = sum(1 for d in decisions if d.allowed)
    blocked = sum(1 for d in decisions if not d.allowed)

    status = "PHASE2_SOFT_BLOCK_READY"
    if not git_clean():
        status = "WARN_GIT_DIRTY"
    elif allowed <= 0:
        status = "FAIL_NO_ALLOWED_CASE"
    elif blocked <= 0:
        status = "FAIL_NO_BLOCKED_CASE"

    print(
        "RUNTIME_EDGE_GOVERNANCE_PHASE2_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"allowed={allowed}",
        f"soft_blocked={blocked}",
        flush=True,
    )

    print(
        "RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
