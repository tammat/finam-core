#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_AUDIT_V1 — read-only аудит insert/save path.
# Ничего не меняет в коде, БД, runtime, systemd и execution.
# Цель — понять, почему runtime_guard_pre_signal_block_audit_v1 получает
# strategy=MEAN_REVERSION_EQUITY при уже пропатченных callsite-ах.


TARGET_FILES = [
    Path("src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py"),
    Path("src/finam_core/pipelines/paper_pipeline.py"),
]


PATTERNS = (
    "class RuntimeGuardPreSignalBlockAuditV1",
    "def save(",
    "runtime_guard_pre_signal_block_audit_v1",
    "strategy",
    "MEAN_REVERSION_EQUITY",
    "DEFAULT_STRATEGY",
    "SYMBOL_STRATEGY_MAP",
    "insert into",
    "INSERT INTO",
    "execute(",
    "payload",
)


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def context(lines: list[str], lineno: int, before: int = 12, after: int = 45) -> list[tuple[int, str]]:
    start = max(1, lineno - before)
    end = min(len(lines), lineno + after)
    return [(i, lines[i - 1]) for i in range(start, end + 1)]


def find_defs(lines: list[str], names: tuple[str, ...]) -> list[int]:
    out: list[int] = []
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if any(stripped.startswith(f"def {name}") for name in names):
            out.append(idx)
    return out


def collect_function(lines: list[str], def_lineno: int) -> list[tuple[int, str]]:
    if def_lineno <= 0:
        return []

    rows: list[tuple[int, str]] = []
    base_indent = len(lines[def_lineno - 1]) - len(lines[def_lineno - 1].lstrip())

    for idx in range(def_lineno, len(lines) + 1):
        line = lines[idx - 1]
        stripped = line.strip()

        if idx > def_lineno and (stripped.startswith("def ") or stripped.startswith("class ")):
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                break

        rows.append((idx, line))

    return rows


def main() -> int:
    print("=== EQUITY PRE SIGNAL GUARD INSERT PATH AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("file_update=0")
    print()

    print("EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_FILES")
    file_texts: dict[Path, str] = {}
    file_lines: dict[Path, list[str]] = {}

    for path in TARGET_FILES:
        lines = read_lines(path)
        text = "\n".join(lines)
        file_lines[path] = lines
        file_texts[path] = text
        print(
            "EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_FILE "
            f"path={path} "
            f"exists={1 if path.exists() else 0} "
            f"lines={len(lines)} "
            f"size={path.stat().st_size if path.exists() else 0}"
        )

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_PATTERN_ROWS")
    for path, text in file_texts.items():
        for pattern in PATTERNS:
            count = text.count(pattern)
            if count:
                print(
                    "EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_PATTERN_ROW "
                    f"path={path} "
                    f"pattern=\"{pattern}\" "
                    f"count={count}"
                )

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_MATCH_LINES")
    for path, lines in file_lines.items():
        for idx, line in enumerate(lines, 1):
            if any(pattern in line for pattern in PATTERNS):
                print(
                    "EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_MATCH_LINE "
                    f"path={path} "
                    f"lineno={idx} "
                    f"line=\"{line.strip()}\""
                )

    analytics_path = Path("src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py")
    analytics_lines = file_lines.get(analytics_path, [])

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_SAVE_FUNCTIONS")
    save_def_lines = find_defs(analytics_lines, ("save(", "migrate("))
    for lineno in save_def_lines:
        print(
            "EQUITY_PRE_SIGNAL_GUARD_SAVE_FUNCTION "
            f"path={analytics_path} "
            f"lineno={lineno} "
            f"line=\"{analytics_lines[lineno - 1].strip()}\""
        )
        print("EQUITY_PRE_SIGNAL_GUARD_SAVE_FUNCTION_CONTEXT_BEGIN")
        for no, ctx_line in collect_function(analytics_lines, lineno):
            print(f"{no}: {ctx_line}")
        print("EQUITY_PRE_SIGNAL_GUARD_SAVE_FUNCTION_CONTEXT_END")

    analytics_text = file_texts.get(analytics_path, "")

    save_exists = "def save(" in analytics_text
    save_mentions_strategy = "strategy" in analytics_text
    save_mentions_default_strategy = "DEFAULT_STRATEGY" in analytics_text or "MEAN_REVERSION_EQUITY" in analytics_text
    save_mentions_symbol_map = "SYMBOL_STRATEGY_MAP" in analytics_text
    save_has_insert = "insert into" in analytics_text.lower()
    save_uses_payload_strategy = "payload" in analytics_text and "strategy" in analytics_text

    pipeline_text = file_texts.get(Path("src/finam_core/pipelines/paper_pipeline.py"), "")
    direct_table_writes_in_pipeline = "runtime_guard_pre_signal_block_audit_v1" in pipeline_text and "insert into runtime_guard_pre_signal_block_audit_v1" in pipeline_text.lower()

    likely_save_override = save_mentions_default_strategy or save_mentions_symbol_map

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_AUDIT_SUMMARY")
    print(f"save_exists={1 if save_exists else 0}")
    print(f"save_mentions_strategy={1 if save_mentions_strategy else 0}")
    print(f"save_has_insert={1 if save_has_insert else 0}")
    print(f"save_mentions_default_strategy={1 if save_mentions_default_strategy else 0}")
    print(f"save_mentions_symbol_map={1 if save_mentions_symbol_map else 0}")
    print(f"save_uses_payload_strategy={1 if save_uses_payload_strategy else 0}")
    print(f"direct_table_writes_in_pipeline={1 if direct_table_writes_in_pipeline else 0}")
    print(f"likely_save_override={1 if likely_save_override else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("file_update=0")

    if likely_save_override:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_SAVE_PATH_STRATEGY_OVERRIDE_SUSPECTED")
    elif save_exists and save_has_insert and save_mentions_strategy:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_SAVE_PATH_PASSES_STRATEGY_REVIEW_REQUIRED")
    elif direct_table_writes_in_pipeline:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_DIRECT_PIPELINE_WRITE_REVIEW_REQUIRED")
    else:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_NEEDS_MANUAL_REVIEW")

    print("EQUITY_PRE_SIGNAL_GUARD_INSERT_PATH_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
