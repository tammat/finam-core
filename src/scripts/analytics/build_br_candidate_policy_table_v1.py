from __future__ import annotations

import argparse
import subprocess
import sys


ROLLOUT_STATUS = {
    "ALLOW": "READY",
    "SOFT_BLOCK": "READY",
    "HIGH_RISK_OBSERVE": "INVESTIGATE",
    "STALE_FINANCIAL_OBSERVE": "WAIT",
    "OBSERVE": "WAIT",
}


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def parse_policy_line(line: str) -> dict[str, str]:
    result: dict[str, str] = {}

    for part in line.strip().split()[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key] = value

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--min-closed-trades", type=int, default=5)
    parser.add_argument("--min-governance-rows", type=int, default=5)
    args = parser.parse_args()

    print("BR_POLICY_TABLE_V1", flush=True)
    print(
        "BR_POLICY_TABLE_CONFIG "
        f"window_days={args.window_days} "
        f"min_closed_trades={args.min_closed_trades} "
        f"min_governance_rows={args.min_governance_rows} "
        f"git_clean={git_clean()}",
        flush=True,
    )

    cmd = [
        sys.executable,
        "src/scripts/analytics/build_br_governance_alpha_v2.py",
        "--window-days",
        str(args.window_days),
        "--min-closed-trades",
        str(args.min_closed_trades),
        "--min-governance-rows",
        str(args.min_governance_rows),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(f"BR_POLICY_TABLE_SOURCE_FAILED stderr={result.stderr.strip()}", flush=True)
        return result.returncode

    rows = []
    for line in result.stdout.splitlines():
        if not line.startswith("BR_POLICY_CANDIDATE "):
            continue

        item = parse_policy_line(line)
        action = item.get("action", "OBSERVE")
        item["rollout_status"] = ROLLOUT_STATUS.get(action, "WAIT")
        rows.append(item)

    for item in sorted(rows, key=lambda x: (int(x.get("hour_msk", "999")), x.get("side", ""))):
        print(
            "BR_POLICY_TABLE_ROW "
            f"hour_msk={item.get('hour_msk')} "
            f"side={item.get('side')} "
            f"candidate_action={item.get('action')} "
            f"rollout_status={item.get('rollout_status')} "
            f"sample_quality={item.get('sample_quality')} "
            f"closed_trades={item.get('closed_trades')} "
            f"net_pnl_sum={item.get('net_pnl_sum')} "
            f"governance_rows={item.get('governance_rows')} "
            f"avg_governance_expectancy={item.get('avg_governance_expectancy')} "
            f"reason={item.get('reason')}",
            flush=True,
        )

    summary: dict[str, int] = {}
    for item in rows:
        rollout = item["rollout_status"]
        summary[rollout] = summary.get(rollout, 0) + 1

    for rollout, count in sorted(summary.items()):
        print(f"BR_POLICY_TABLE_SUMMARY rollout_status={rollout} rows={count}", flush=True)

    print("BR_POLICY_TABLE_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
