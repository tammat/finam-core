#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess

SYMBOL = os.getenv("GOLD_SYMBOL", "GDU6@RTSX")

COMMANDS = {
    "scorecard": [
        "python3",
        "src/scripts/research/build_runtime_shadow_validation_gold_scorecard_v1.py",
    ],
    "audit": [
        "python3",
        "src/scripts/research/build_runtime_shadow_validation_gold_scorecard_audit_v1.py",
    ],
    "walkforward": [
        "python3",
        "src/scripts/research/build_runtime_shadow_validation_gold_walkforward_v1.py",
    ],
}


def run_step(name: str, cmd: list[str]) -> tuple[bool, str]:
    env = os.environ.copy()
    env["GOLD_SYMBOL"] = SYMBOL

    result = subprocess.run(
        cmd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    return result.returncode == 0, result.stdout


def has(text: str, marker: str) -> bool:
    return marker in text


def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD PROMOTION REVIEW V1 ===")
    print("mode=promotion_review")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    outputs: dict[str, str] = {}
    ok_flags: dict[str, bool] = {}

    for name, cmd in COMMANDS.items():
        ok, out = run_step(name, cmd)
        outputs[name] = out
        ok_flags[name] = ok

    scorecard_ok = (
        ok_flags["scorecard"]
        and has(outputs["scorecard"], "VERDICT=GOLD_SCORECARD_PROMOTE_CANDIDATE")
        and has(outputs["scorecard"], "runtime_allow=0")
        and has(outputs["scorecard"], "execution_enabled=0")
    )

    audit_ok = (
        ok_flags["audit"]
        and has(outputs["audit"], "AUDIT_VERDICT=PASS")
        and has(outputs["audit"], "runtime_allow=0")
        and has(outputs["audit"], "execution_enabled=0")
    )

    walkforward_ok = (
        ok_flags["walkforward"]
        and has(outputs["walkforward"], "VERDICT=GOLD_WALKFORWARD_STABLE")
        and has(outputs["walkforward"], "runtime_allow=0")
        and has(outputs["walkforward"], "execution_enabled=0")
    )

    print("REVIEW_ROWS")
    print(f"REVIEW_ROW step=scorecard status={'PASS' if scorecard_ok else 'FAIL'}")
    print(f"REVIEW_ROW step=audit status={'PASS' if audit_ok else 'FAIL'}")
    print(f"REVIEW_ROW step=walkforward status={'PASS' if walkforward_ok else 'FAIL'}")

    if scorecard_ok and audit_ok and walkforward_ok:
        decision = "WATCH_RUNTIME_CANDIDATE"
        reason = "scorecard_passed_audit_passed_walkforward_stable"
        verdict = "GOLD_PROMOTION_REVIEW_WATCH_RUNTIME_CANDIDATE"
    else:
        decision = "REJECT_OR_CONTINUE_SHADOW"
        reason = "promotion_review_failed"
        verdict = "GOLD_PROMOTION_REVIEW_NOT_READY"

    print()
    print("PROMOTION_REVIEW")
    print(f"decision={decision}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"reason={reason}")
    print(f"VERDICT={verdict}")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_PROMOTION_REVIEW_V1_OK")

    if decision != "WATCH_RUNTIME_CANDIDATE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
