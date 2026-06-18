#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess


# Русский комментарий:
# SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_V1 — финальный read-only review.
# Скрипт не меняет БД, runtime_active_universe, systemd и execution.
# Он только классифицирует результат dry-run: применяем / не применяем / уже применено.


def parse_dry_run_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for line in output.splitlines():
        if not line.startswith("SMART_ENTRY_RETEST_QUARANTINE_DRY_RUN_ROW "):
            continue

        row: dict[str, str] = {}
        for part in line.split()[1:]:
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            row[key] = value

        rows.append(row)

    return rows


def parse_summary(output: str) -> dict[str, str]:
    keys = {
        "plan_rows",
        "runtime_rows",
        "quarantine_runtime_candidates",
        "session_filter_candidates",
        "require_more_data",
        "planned_changes",
        "no_runtime_match",
        "db_update",
    }

    result: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in keys:
            result[key] = value

    return result


def classify_review(row: dict[str, str]) -> tuple[str, str]:
    planned_action = row.get("planned_action", "")
    runtime_symbol = row.get("runtime_symbol", "NONE")
    runtime_enabled = row.get("runtime_is_enabled", "NONE")
    would_change = row.get("would_change", "0")
    target_reason = row.get("target_disable_reason", "NONE")
    strategy = row.get("strategy", "UNKNOWN")

    if planned_action == "QUARANTINE_RUNTIME_CANDIDATE":
        if target_reason == "ALREADY_DISABLED" or runtime_enabled == "False":
            return "NO_APPLY_ALREADY_DISABLED", "runtime_row_already_disabled"

        if runtime_symbol == "NONE":
            return "NO_APPLY_NO_RUNTIME_MATCH", "strategy_not_present_in_runtime_active_universe"

        if would_change == "1":
            return "APPLY_CANDIDATE_REQUIRES_MANUAL_APPROVAL", "dry_run_would_disable_runtime_row"

        return "NO_APPLY_REVIEW_REQUIRED", "quarantine_candidate_without_change"

    if planned_action == "RESEARCH_ONLY_WITH_SESSION_FILTER":
        return "NO_APPLY_RESEARCH_ONLY", "session_filter_hypothesis_only"

    if planned_action == "REQUIRE_MORE_DATA":
        return "NO_APPLY_REQUIRE_MORE_DATA", "insufficient_sample"

    return "NO_APPLY", "no_runtime_action"


def main() -> int:
    print("=== SMART ENTRY RETEST QUARANTINE APPLY PLAN REVIEW V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    proc = subprocess.run(
        ["python3", "src/scripts/research/build_smart_entry_retest_quarantine_apply_dry_run_v1.py"],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if proc.returncode != 0:
        print(proc.stdout)
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_FAILED_DRY_RUN")
        return proc.returncode

    rows = parse_dry_run_rows(proc.stdout)
    summary = parse_summary(proc.stdout)

    apply_candidates = 0
    already_disabled = 0
    no_runtime_match = 0
    research_only = 0
    require_more_data = 0
    no_apply = 0

    print("SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_ROWS")

    for row in rows:
        review_action, review_reason = classify_review(row)

        if review_action == "APPLY_CANDIDATE_REQUIRES_MANUAL_APPROVAL":
            apply_candidates += 1
        elif review_action == "NO_APPLY_ALREADY_DISABLED":
            already_disabled += 1
        elif review_action == "NO_APPLY_NO_RUNTIME_MATCH":
            no_runtime_match += 1
        elif review_action == "NO_APPLY_RESEARCH_ONLY":
            research_only += 1
        elif review_action == "NO_APPLY_REQUIRE_MORE_DATA":
            require_more_data += 1
        else:
            no_apply += 1

        print(
            "SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_ROW "
            f"family={row.get('family', 'UNKNOWN')} "
            f"strategy={row.get('strategy', 'UNKNOWN')} "
            f"timeframe={row.get('timeframe', 'UNKNOWN')} "
            f"continuous_symbol={row.get('continuous_symbol', 'UNKNOWN')} "
            f"planned_action={row.get('planned_action', 'UNKNOWN')} "
            f"runtime_symbol={row.get('runtime_symbol', 'NONE')} "
            f"runtime_strategy={row.get('runtime_strategy', 'NONE')} "
            f"runtime_timeframe={row.get('runtime_timeframe', 'NONE')} "
            f"runtime_is_enabled={row.get('runtime_is_enabled', 'NONE')} "
            f"would_change={row.get('would_change', '0')} "
            f"target_disable_reason={row.get('target_disable_reason', 'NONE')} "
            f"review_action={review_action} "
            f"review_reason={review_reason}"
        )

    print()
    print("SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_SUMMARY")
    print(f"plan_rows={summary.get('plan_rows', str(len(rows)))}")
    print(f"runtime_rows={summary.get('runtime_rows', '0')}")
    print(f"dry_run_planned_changes={summary.get('planned_changes', '0')}")
    print(f"dry_run_no_runtime_match={summary.get('no_runtime_match', '0')}")
    print(f"apply_candidates={apply_candidates}")
    print(f"already_disabled={already_disabled}")
    print(f"no_runtime_match={no_runtime_match}")
    print(f"research_only={research_only}")
    print(f"require_more_data={require_more_data}")
    print(f"no_apply={no_apply}")
    print("db_update=0")

    if apply_candidates > 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_MANUAL_APPROVAL_REQUIRED")
    elif already_disabled > 0 or no_runtime_match > 0:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_NO_DB_CHANGE_REQUIRED")
    else:
        print("VERDICT=SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_RESEARCH_ONLY")

    print("SMART_ENTRY_RETEST_QUARANTINE_APPLY_PLAN_REVIEW_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
