#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess


# Русский комментарий:
# SMART_ENTRY_RETEST_QUARANTINE_PLAN_V1 — read-only план карантина для smart_entry_retest.
# Скрипт не меняет БД, runtime_active_universe, systemd и execution.
# Источник — результат SMART_ENTRY_RETEST_FAILURE_ANALYSIS_V1.


def parse_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in output.splitlines():
        if not line.startswith("SMART_ENTRY_RETEST_STRATEGY_ROW "):
            continue

        row: dict[str, str] = {}
        for part in line.split()[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            row[key] = value

        rows.append(row)

    return rows


def as_int(row: dict[str, str], key: str) -> int:
    return int(float(row.get(key, "0")))


def as_float(row: dict[str, str], key: str) -> float:
    return float(row.get(key, "0"))


def decide_action(row: dict[str, str]) -> tuple[str, str]:
    family = row.get("family", "UNKNOWN")
    strategy = row.get("strategy", "UNKNOWN")
    timeframe = row.get("timeframe", "UNKNOWN")
    continuous_symbol = row.get("continuous_symbol", "UNKNOWN")

    pairs = as_int(row, "pairs")
    wins = as_int(row, "wins")
    losses = as_int(row, "losses")
    winrate = as_float(row, "winrate")
    net_pnl = as_float(row, "net_pnl")
    net_pnl_per_pair = as_float(row, "net_pnl_per_pair")

    if pairs == 0:
        return "NO_ACTION", "no_pairs"

    if family == "FX_USDRUB" and pairs >= 10 and wins == 0:
        return "QUARANTINE_RUNTIME_CANDIDATE", "zero_winrate_usdrub_smart_retest"

    if family == "ENERGY_OIL" and strategy == "BR_CONSERVATIVE_BREAKOUT" and pairs >= 30 and net_pnl < 0:
        return "QUARANTINE_RUNTIME_CANDIDATE", "br_smart_retest_material_negative_edge"

    if family == "ENERGY_GAS" and strategy == "NG_CONSERVATIVE_BREAKOUT" and timeframe == "M5":
        if pairs >= 50 and net_pnl < 0 and winrate < 0.30:
            return "RESEARCH_ONLY_WITH_SESSION_FILTER", "ng_m5_smart_retest_negative_but_filterable"
        return "KEEP_RESEARCH_ONLY", "ng_m5_smart_retest_requires_more_data"

    if family == "ENERGY_GAS" and strategy == "NG_CONSERVATIVE_BREAKOUT_M1":
        if pairs < 20:
            return "REQUIRE_MORE_DATA", "ng_m1_or_live_sample_too_small"
        if net_pnl < 0:
            return "KEEP_RESEARCH_ONLY", "ng_m1_or_live_negative_edge"
        return "KEEP_RESEARCH_ONLY", "ng_m1_or_live_not_confirmed"

    if net_pnl < 0 and pairs >= 20:
        return "QUARANTINE_RUNTIME_CANDIDATE", "generic_smart_retest_negative_edge"

    if net_pnl < 0:
        return "KEEP_RESEARCH_ONLY", "negative_but_sample_small"

    if net_pnl_per_pair < 0.01:
        return "KEEP_RESEARCH_ONLY", "micro_edge_below_execution_threshold"

    return "REQUIRE_MORE_DATA", "not_enough_evidence_for_runtime"


def main() -> int:
    print("=== SMART ENTRY RETEST QUARANTINE PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print()

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    proc = subprocess.run(
        ["python3", "src/scripts/research/build_smart_entry_retest_failure_analysis_v1.py"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_PLAN_FAILED_ANALYSIS")
        return proc.returncode

    rows = parse_rows(proc.stdout)

    quarantine = 0
    research_only = 0
    session_filter = 0
    require_more_data = 0
    no_action = 0

    print("SMART_ENTRY_RETEST_QUARANTINE_PLAN_ROWS")

    for row in rows:
        action, reason = decide_action(row)

        if action == "QUARANTINE_RUNTIME_CANDIDATE":
            quarantine += 1
        elif action == "RESEARCH_ONLY_WITH_SESSION_FILTER":
            session_filter += 1
        elif action == "KEEP_RESEARCH_ONLY":
            research_only += 1
        elif action == "REQUIRE_MORE_DATA":
            require_more_data += 1
        else:
            no_action += 1

        print(
            "SMART_ENTRY_RETEST_QUARANTINE_PLAN_ROW "
            f"family={row.get('family', 'UNKNOWN')} "
            f"strategy={row.get('strategy', 'UNKNOWN')} "
            f"timeframe={row.get('timeframe', 'UNKNOWN')} "
            f"continuous_symbol={row.get('continuous_symbol', 'UNKNOWN')} "
            f"pairs={row.get('pairs', '0')} "
            f"wins={row.get('wins', '0')} "
            f"losses={row.get('losses', '0')} "
            f"winrate={row.get('winrate', '0')} "
            f"net_pnl={row.get('net_pnl', '0')} "
            f"net_pnl_per_pair={row.get('net_pnl_per_pair', '0')} "
            f"planned_action={action} "
            f"reason={reason}"
        )

    print()
    print("SMART_ENTRY_RETEST_QUARANTINE_PLAN_SUMMARY")
    print(f"rows_total={len(rows)}")
    print(f"quarantine_runtime_candidates={quarantine}")
    print(f"research_only={research_only}")
    print(f"research_only_with_session_filter={session_filter}")
    print(f"require_more_data={require_more_data}")
    print(f"no_action={no_action}")

    if len(rows) == 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_PLAN_EMPTY")
    elif quarantine > 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_PLAN_RESTRICTIVE")
    else:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_PLAN_RESEARCH_ONLY")

    print("SMART_ENTRY_RETEST_QUARANTINE_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
