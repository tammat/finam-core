#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess


PATTERNS = {
    "sell_candidate": r"BR_MANUAL_ENTRY_CANDIDATE symbol=BR.* side=SELL",
    "buy_candidate": r"BR_MANUAL_ENTRY_CANDIDATE symbol=BR.* side=BUY",
    "strict_edge_sell": r"PIPE_BR_STRICT_EDGE_ADVISORY_CONTINUE symbol=BR.* side=SELL",
    "strict_edge_buy": r"PIPE_BR_STRICT_EDGE_ADVISORY_CONTINUE symbol=BR.* side=BUY",
    "risk_ctx": r"PIPE_RISK_CTX symbol=BR",
    "risk_ok": r"PIPE_RISK_OK",
    "portfolio_risk_ok": r"PIPE_PORTFOLIO_RISK_OK",
    "anti_reentry": r"PIPE_ANTI_REENTRY_BLOCK .*symbol=BR",
    "short_policy": r"PIPE_BR_SHORT_SHADOW_POLICY_V1",
    "long_governance": r"PIPE_BR_LONG_GOVERNANCE_V1",
    "paper_fill": r"PIPE_FILLED paper BR",
    "exit_engine_sell": r"PIPE_EXIT_ENGINE_SIGNAL symbol=BR.*close_side=SELL",
    "error": r"Traceback|ERROR|Exception",
}


def journal(unit: str, since: str, until: str | None) -> str:
    cmd = ["journalctl", "-u", unit, "--since", since, "--no-pager"]
    if until:
        cmd.extend(["--until", until])
    result = subprocess.run(cmd, check=False, text=True, capture_output=True)
    return (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text))


def lines(pattern: str, text: str) -> list[str]:
    return [line for line in text.splitlines() if re.search(pattern, line)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", default="finam-paper-pipeline.service")
    parser.add_argument("--since", default="2026-06-06 10:10:00")
    parser.add_argument("--until", default="2026-06-06 10:23:00")
    args = parser.parse_args()

    text = journal(args.unit, args.since, args.until)

    print("=== BR SHORT POLICY REACHABILITY AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"unit={args.unit}")
    print(f"since={args.since}")
    print(f"until={args.until}")
    print()

    print("SUMMARY")
    metrics = {name: count(pattern, text) for name, pattern in PATTERNS.items()}
    for name, value in metrics.items():
        print(f"METRIC_ROW name={name} rows={value}")
    print()

    print("TRACE_ROWS")
    trace_pattern = (
        r"BR_MANUAL_ENTRY_CANDIDATE symbol=BR|"
        r"PIPE_BR_STRICT_EDGE_ADVISORY_CONTINUE symbol=BR|"
        r"PIPE_RISK_CTX symbol=BR|"
        r"PIPE_RISK_OK|"
        r"PIPE_PORTFOLIO_RISK_OK|"
        r"PIPE_ANTI_REENTRY_BLOCK .*symbol=BR|"
        r"PIPE_BR_SHORT_SHADOW_POLICY_V1|"
        r"PIPE_BR_LONG_GOVERNANCE_V1|"
        r"PIPE_FILLED paper BR|"
        r"PIPE_EXIT_ENGINE_SIGNAL symbol=BR|"
        r"Traceback|ERROR|Exception"
    )
    trace_rows = lines(trace_pattern, text)
    if trace_rows:
        for row in trace_rows[-200:]:
            print(f"TRACE_ROW {row}")
    else:
        print("NONE")
    print()

    sell_candidates = metrics["sell_candidate"]
    short_policy = metrics["short_policy"]
    strict_edge_sell = metrics["strict_edge_sell"]
    risk_ctx = metrics["risk_ctx"]
    anti_reentry = metrics["anti_reentry"]
    errors = metrics["error"]

    if errors:
        verdict = "CHECK_RUNTIME_ERRORS"
    elif sell_candidates == 0:
        verdict = "NO_BR_SELL_ENTRY_IN_WINDOW"
    elif sell_candidates > 0 and strict_edge_sell == 0 and risk_ctx == 0:
        verdict = "BR_SELL_DROPPED_AFTER_CANDIDATE_BEFORE_STRICT_EDGE"
    elif sell_candidates > 0 and strict_edge_sell > 0 and short_policy == 0 and anti_reentry > 0:
        verdict = "BR_SELL_BLOCKED_BEFORE_SHORT_POLICY_BY_ANTI_REENTRY_OR_POSITION"
    elif sell_candidates > 0 and strict_edge_sell > 0 and short_policy == 0:
        verdict = "BR_SELL_PASSED_STRICT_EDGE_BUT_NOT_SHORT_POLICY"
    elif short_policy > 0:
        verdict = "BR_SHORT_POLICY_REACHED"
    else:
        verdict = "UNKNOWN"

    print(f"VERDICT={verdict}")
    print("BR_SHORT_POLICY_REACHABILITY_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
