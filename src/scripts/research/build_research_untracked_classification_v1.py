#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

KEEP_HINTS = (
    "session_filter_replay",
    "session_filter_walkforward",
    "failure_decomposition",
    "forward_accumulation",
    "edge_stability_report",
)

REVIEW_HINTS = (
    "equity_vol_breakout_parameter_research",
    "multi_asset_compression_follow_through",
    "clean_subset_replay",
    "forward_decay_audit",
)

DROP_HINTS = (
    "strategy_name_resolver_patch",
)

def git_untracked() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"],
        text=True,
    )
    return sorted(
        line.strip()
        for line in out.splitlines()
        if line.strip()
        and (
            line.startswith("src/scripts/research/")
            or line.startswith("scripts/test_")
        )
    )

def classify(path: str) -> tuple[str, str]:
    name = Path(path).name

    if any(h in name for h in KEEP_HINTS):
        return "KEEP_AND_COMMIT", "used_in_current_rs_bottom_edge_workflow"

    if any(h in name for h in REVIEW_HINTS):
        return "REVIEW_BEFORE_COMMIT", "research_value_possible_but_not_runtime_blocking"

    if any(h in name for h in DROP_HINTS):
        return "DROP_OR_ARCHIVE_CANDIDATE", "patch_plan_or_superseded_diagnostic"

    if "research_untracked_audit" in name:
        return "KEEP_AND_COMMIT", "meta_audit_tool"

    return "REVIEW_BEFORE_COMMIT", "unclassified_research_artifact"

def main() -> int:
    print("=== RESEARCH_UNTRACKED_CLASSIFICATION_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")

    files = git_untracked()

    counts: dict[str, int] = {}

    print("\nCLASSIFICATION_ROWS")
    for f in files:
        cls, reason = classify(f)
        counts[cls] = counts.get(cls, 0) + 1
        print(f"CLASSIFICATION_ROW file={f} classification={cls} reason={reason}")

    print("\nCLASSIFICATION_SUMMARY")
    print(f"files_total={len(files)}")
    for k in sorted(counts):
        print(f"{k}={counts[k]}")

    if files:
        print("VERDICT=RESEARCH_UNTRACKED_CLASSIFICATION_READY")
    else:
        print("VERDICT=RESEARCH_UNTRACKED_CLASSIFICATION_EMPTY")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
