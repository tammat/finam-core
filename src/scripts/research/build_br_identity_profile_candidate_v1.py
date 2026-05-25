from __future__ import annotations

import subprocess


CANDIDATE_NAME = "BR_ASIA_SCALP_MEDIUM_MOVE"


def main() -> int:
    result = subprocess.run(
        ["python", "src/scripts/research/build_br_strategy_identity_summary_v1.py"],
        check=True,
        text=True,
        capture_output=True,
    )

    target_line = ""
    for line in result.stdout.splitlines():
        if line.startswith("ASIA/SCALP_LT_5M/MEDIUM_MOVE/PASS"):
            target_line = line
            break

    if not target_line:
        print("BR_IDENTITY_PROFILE_CANDIDATE_V1")
        print(f"candidate={CANDIDATE_NAME}")
        print("status=NOT_FOUND")
        print("reason=target_profile_not_found")
        print("BR_IDENTITY_PROFILE_CANDIDATE_V1_OK status=NOT_FOUND")
        return 0

    parts = [x.strip() for x in target_line.split("|")]
    count = int(parts[1])
    ratio = float(parts[2])

    if count >= 40 and ratio >= 0.30:
        status = "RESEARCH_PROFILE_CANDIDATE"
        reason = "dominant_clean_pass_profile_found"
    else:
        status = "LOW_SAMPLE_PROFILE"
        reason = "profile_sample_or_ratio_too_low"

    print("BR_IDENTITY_PROFILE_CANDIDATE_V1")
    print(f"candidate={CANDIDATE_NAME}")
    print("source_strategy=BR_CONSERVATIVE_BREAKOUT")
    print("profile=ASIA/SCALP_LT_5M/MEDIUM_MOVE/PASS")
    print(f"trades={count}")
    print(f"ratio={ratio:.6f}")
    print(f"status={status}")
    print("runtime_enabled=false")
    print("research_only=true")
    print(f"reason={reason}")
    print(f"BR_IDENTITY_PROFILE_CANDIDATE_V1_OK status={status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
