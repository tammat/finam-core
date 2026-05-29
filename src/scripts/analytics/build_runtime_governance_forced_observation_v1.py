from __future__ import annotations

import argparse
import subprocess

from finam_core.execution.runtime_edge_governance_soft_block_v1 import (
    RuntimeEdgeGovernanceSoftBlockV1,
)
from finam_core.execution.runtime_governance_live_accumulation_v1 import (
    RuntimeGovernanceLiveAccumulatorV1,
    RuntimeGovernanceLiveDecisionV1,
)


SOURCE = "forced_runtime_governance_observation_v1"


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRN6@RTSX")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--sides", default="BUY,SELL")
    args = parser.parse_args()

    sides = [
        side.strip().upper()
        for side in args.sides.split(",")
        if side.strip()
    ]

    governance = RuntimeEdgeGovernanceSoftBlockV1()
    accumulator = RuntimeGovernanceLiveAccumulatorV1()
    accumulator.ensure_schema()

    written = 0

    print("RUNTIME_GOVERNANCE_FORCED_OBSERVATION_V1")
    print(
        "RUNTIME_GOVERNANCE_FORCED_OBSERVATION_START",
        f"symbol={args.symbol}",
        f"runs={args.runs}",
        f"sides={','.join(sides)}",
        f"source={SOURCE}",
        f"git_clean={git_clean()}",
        flush=True,
    )

    for run_no in range(1, args.runs + 1):
        for side in sides:
            decision = governance.decide(
                symbol=str(args.symbol),
                side=str(side),
            )

            accumulator.append(
                RuntimeGovernanceLiveDecisionV1(
                    symbol=str(decision.symbol),
                    side=str(decision.side),
                    hour_msk=int(decision.hour_msk),
                    allowed=bool(decision.allowed),
                    action=str(decision.action),
                    reason=str(decision.reason),
                    session_action=decision.session_action,
                    strict_reason=decision.strict_reason,
                    decay_state=decision.decay_state,
                    expectancy_points=decision.expectancy_points,
                    closed_trades=decision.closed_trades,
                    raw_json={
                        "source": SOURCE,
                        "mode": "forced_observation_no_order",
                        "run_no": run_no,
                    },
                )
            )

            written += 1

            print(
                "RUNTIME_GOVERNANCE_FORCED_OBSERVATION_ROW",
                f"run_no={run_no}",
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

    status = "FORCED_OBSERVATION_WRITTEN" if written > 0 else "NO_ROWS_WRITTEN"

    print(
        "RUNTIME_GOVERNANCE_FORCED_OBSERVATION_STATUS",
        f"status={status}",
        f"written_rows={written}",
        f"source={SOURCE}",
        flush=True,
    )

    print(
        f"RUNTIME_GOVERNANCE_FORCED_OBSERVATION_V1_OK status={status}",
        flush=True,
    )

    return 0 if written > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
