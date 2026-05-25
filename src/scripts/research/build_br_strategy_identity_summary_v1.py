from __future__ import annotations

import subprocess
from collections import Counter


def main() -> int:
    cmd = [
        "python",
        "src/scripts/research/build_br_strategy_identity_guard_v1.py",
    ]

    result = subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=True,
    )

    decision_counter: Counter[str] = Counter()
    reason_counter: Counter[str] = Counter()
    combo_counter: Counter[str] = Counter()

    in_rows = False

    for line in result.stdout.splitlines():
        if line.startswith("closed_trade_id |"):
            in_rows = True
            continue

        if line.startswith("SUMMARY"):
            in_rows = False

        if not in_rows or "|" not in line:
            continue

        parts = [x.strip() for x in line.split("|")]
        if len(parts) < 6:
            continue

        session = parts[1]
        duration_bucket = parts[2]
        move_bucket = parts[3]
        decision = parts[4]
        reason = parts[5]

        decision_counter[decision] += 1
        combo_counter[f"{session}/{duration_bucket}/{move_bucket}/{decision}"] += 1

        for item in reason.split(";"):
            item = item.strip()
            if item and item != "identity_profile_matched":
                reason_counter[item] += 1

    total = sum(decision_counter.values())

    print("BR_STRATEGY_IDENTITY_SUMMARY_V1")
    print(f"total={total}")

    print("DECISION_SUMMARY")
    print("decision | count | ratio")
    for decision, count in decision_counter.most_common():
        ratio = count / total if total else 0.0
        print(f"{decision} | {count} | {ratio:.6f}")

    print("TOP_REASONS")
    print("reason | count | ratio")
    for reason, count in reason_counter.most_common(20):
        ratio = count / total if total else 0.0
        print(f"{reason} | {count} | {ratio:.6f}")

    print("TOP_COMBINATIONS")
    print("combination | count | ratio")
    for combo, count in combo_counter.most_common(20):
        ratio = count / total if total else 0.0
        print(f"{combo} | {count} | {ratio:.6f}")

    fail_ratio = decision_counter["FAIL"] / total if total else 0.0
    pass_ratio = decision_counter["PASS"] / total if total else 0.0

    if fail_ratio >= 0.50:
        verdict = "IDENTITY_BROKEN_BY_MIXED_BEHAVIOR"
    elif pass_ratio >= 0.50:
        verdict = "IDENTITY_DOMINANT_PROFILE_FOUND"
    else:
        verdict = "IDENTITY_MIXED_WATCH"

    print("SUMMARY")
    print(f"pass_ratio={pass_ratio:.6f}")
    print(f"fail_ratio={fail_ratio:.6f}")
    print(f"verdict={verdict}")
    print(f"BR_STRATEGY_IDENTITY_SUMMARY_V1_OK verdict={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
