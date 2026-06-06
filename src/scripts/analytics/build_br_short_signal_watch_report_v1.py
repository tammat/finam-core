#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def _latest_lines(pattern: str, text: str, limit: int = 20) -> list[str]:
    rows = [line for line in text.splitlines() if re.search(pattern, line)]
    return rows[-limit:]


def _journal(unit: str, since: str) -> str:
    cmd = [
        "journalctl",
        "-u",
        unit,
        "--since",
        since,
        "--no-pager",
    ]
    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    return (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", default="finam-paper-pipeline.service")
    parser.add_argument("--since", default="6 hours ago")
    args = parser.parse_args()

    text = _journal(args.unit, args.since)

    br_buy_candidates = _count(r"BR_MANUAL_ENTRY_CANDIDATE symbol=BR.* side=BUY", text)
    br_sell_candidates = _count(r"BR_MANUAL_ENTRY_CANDIDATE symbol=BR.* side=SELL", text)
    br_exit_sell = _count(r"PIPE_EXIT_ENGINE_SIGNAL symbol=BR.* close_side=SELL", text)
    br_exit_duplicate = _count(r"PIPE_EXIT_ENGINE_DUPLICATE_BLOCK symbol=BR.* side=SELL", text)
    br_anti_reentry = _count(r"PIPE_ANTI_REENTRY_BLOCK .*symbol=BR", text)
    br_short_policy = _count(r"PIPE_BR_SHORT_SHADOW_POLICY_V1", text)
    br_long_governance = _count(r"PIPE_BR_LONG_GOVERNANCE_V1", text)
    errors = _count(r"Traceback|ERROR|Exception", text)

    print("=== BR SHORT SIGNAL WATCH REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"unit={args.unit}")
    print(f"since={args.since}")
    print()

    print("SUMMARY")
    print(f"BR_BUY_CANDIDATES={br_buy_candidates}")
    print(f"BR_SELL_ENTRY_CANDIDATES={br_sell_candidates}")
    print(f"BR_EXIT_ENGINE_SELL={br_exit_sell}")
    print(f"BR_EXIT_DUPLICATE_BLOCKS={br_exit_duplicate}")
    print(f"BR_ANTI_REENTRY_BLOCKS={br_anti_reentry}")
    print(f"BR_SHORT_POLICY_ROWS={br_short_policy}")
    print(f"BR_LONG_GOVERNANCE_ROWS={br_long_governance}")
    print(f"ERROR_ROWS={errors}")
    print()

    print("LATEST_BR_SELL_ENTRY_CANDIDATES")
    rows = _latest_lines(r"BR_MANUAL_ENTRY_CANDIDATE symbol=BR.* side=SELL", text)
    if rows:
        for line in rows:
            print(f"LOG_ROW {line}")
    else:
        print("NONE")
    print()

    print("LATEST_BR_EXIT_SELL")
    rows = _latest_lines(r"PIPE_EXIT_ENGINE_SIGNAL symbol=BR.* close_side=SELL", text)
    if rows:
        for line in rows:
            print(f"LOG_ROW {line}")
    else:
        print("NONE")
    print()

    print("LATEST_BR_SHORT_POLICY")
    rows = _latest_lines(r"PIPE_BR_SHORT_SHADOW_POLICY_V1", text)
    if rows:
        for line in rows:
            print(f"LOG_ROW {line}")
    else:
        print("NONE")
    print()

    if errors:
        verdict = "CHECK_RUNTIME_ERRORS"
    elif br_sell_candidates == 0 and br_short_policy == 0:
        verdict = "WAIT_FOR_BR_SELL_ENTRY_SIGNAL"
    elif br_sell_candidates > 0 and br_short_policy == 0:
        verdict = "BR_SELL_ENTRY_NOT_REACHING_SHORT_POLICY"
    elif br_short_policy > 0:
        verdict = "BR_SHORT_POLICY_ACTIVE"
    else:
        verdict = "UNKNOWN"

    print(f"VERDICT={verdict}")
    print("BR_SHORT_SIGNAL_WATCH_REPORT_V1_OK")


if __name__ == "__main__":
    main()
