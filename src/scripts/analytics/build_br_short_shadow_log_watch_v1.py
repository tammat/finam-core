#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess


def run_journal(unit: str, since: str) -> list[str]:
    cmd = [
        "journalctl",
        "-u", unit,
        "--since", since,
        "--no-pager",
    ]
    out = subprocess.check_output(cmd, text=True, errors="replace")
    return out.splitlines()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--unit", default="finam-paper-pipeline.service")
    p.add_argument("--since", default="6 hours ago")
    args = p.parse_args()

    print("=== BR SHORT SHADOW LOG WATCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"unit={args.unit}")
    print(f"since={args.since}")
    print()

    lines = run_journal(args.unit, args.since)

    sell_candidates = [
        x for x in lines
        if "BR_MANUAL_ENTRY_CANDIDATE" in x
        and "symbol=BRN6@RTSX" in x
        and "side=SELL" in x
    ]

    shadow_policy = [
        x for x in lines
        if "PIPE_BR_SHORT_SHADOW_POLICY_V1" in x
    ]

    shadow_ok = [
        x for x in lines
        if "PIPE_BR_SHORT_SHADOW_ACCUMULATION_OK" in x
    ]

    route_errors = [
        x for x in lines
        if "PIPE_BR_SHORT_SHADOW" in x and ("ERROR" in x or "Traceback" in x)
    ]

    tracebacks = [x for x in lines if "Traceback" in x]
    errors = [x for x in lines if "ERROR" in x]

    print("SUMMARY")
    print(f"BR_SELL_CANDIDATES={len(sell_candidates)}")
    print(f"BR_SHORT_SHADOW_POLICY_ROWS={len(shadow_policy)}")
    print(f"BR_SHORT_SHADOW_ACCUMULATION_ROWS={len(shadow_ok)}")
    print(f"BR_SHORT_SHADOW_ROUTE_ERRORS={len(route_errors)}")
    print(f"TRACEBACK_ROWS={len(tracebacks)}")
    print(f"ERROR_ROWS={len(errors)}")
    print()

    print("LATEST_BR_SELL_CANDIDATES")
    if not sell_candidates:
        print("NONE")
    for row in sell_candidates[-20:]:
        print(f"LOG_ROW {row}")
    print()

    print("LATEST_BR_SHORT_SHADOW_POLICY")
    if not shadow_policy:
        print("NONE")
    for row in shadow_policy[-20:]:
        print(f"LOG_ROW {row}")
    print()

    print("LATEST_BR_SHORT_SHADOW_ACCUMULATION")
    if not shadow_ok:
        print("NONE")
    for row in shadow_ok[-20:]:
        print(f"LOG_ROW {row}")
    print()

    if len(sell_candidates) == 0:
        verdict = "WAIT_FOR_BR_SELL_CANDIDATE"
    elif len(shadow_policy) == 0:
        verdict = "BR_SELL_NOT_REACHING_SHADOW_POLICY"
    elif len(shadow_ok) == 0:
        verdict = "BR_SHADOW_POLICY_NOT_ACCUMULATING"
    elif route_errors:
        verdict = "BR_SHADOW_ROUTE_ERRORS"
    else:
        verdict = "BR_SHORT_SHADOW_ROUTE_ACTIVE"

    print(f"VERDICT={verdict}")
    print("BR_SHORT_SHADOW_LOG_WATCH_V1_OK")


if __name__ == "__main__":
    main()
