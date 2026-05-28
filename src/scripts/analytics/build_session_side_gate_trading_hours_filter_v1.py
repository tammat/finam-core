from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SOURCE_PATH = Path("runtime/session_side_execution_gate_v1.json")
FILTERED_PATH = Path("runtime/session_side_execution_gate_trading_hours_v1.json")
BACKUP_PATH = Path("runtime/session_side_execution_gate_v1.before_trading_hours_filter_v1.json")


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def hour_allowed(row: dict, min_hour: int, max_hour: int) -> bool:
    hour = int(row.get("hour_msk"))
    return min_hour <= hour <= max_hour


def filter_rows(rows: list[dict], min_hour: int, max_hour: int) -> tuple[list[dict], int]:
    kept = []
    removed = 0

    for row in rows:
        if hour_allowed(row, min_hour, max_hour):
            kept.append(row)
        else:
            removed += 1

    return kept, removed


def main() -> int:
    min_hour = int(os.getenv("BR_TRADING_HOUR_MIN_MSK", "9"))
    max_hour = int(os.getenv("BR_TRADING_HOUR_MAX_MSK", "23"))

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    result = dict(source)

    total_removed = 0
    total_kept = 0

    for section in ("allow", "block", "insufficient_data"):
        rows = list(source.get(section, []) or [])
        filtered, removed = filter_rows(rows, min_hour, max_hour)

        result[section] = filtered
        total_removed += removed
        total_kept += len(filtered)

        print(
            "SESSION_SIDE_GATE_TRADING_HOURS_FILTER_SECTION",
            f"section={section}",
            f"before={len(rows)}",
            f"after={len(filtered)}",
            f"removed={removed}",
            flush=True,
        )

    result["trading_hours_filter_v1"] = {
        "enabled": True,
        "min_hour_msk": min_hour,
        "max_hour_msk": max_hour,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE_PATH),
        "backup": str(BACKUP_PATH),
    }

    if not BACKUP_PATH.exists():
        shutil.copyfile(SOURCE_PATH, BACKUP_PATH)

    FILTERED_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    shutil.copyfile(FILTERED_PATH, SOURCE_PATH)

    status = "OK" if git_clean() else "WARN_GIT_DIRTY"

    print("SESSION_SIDE_GATE_TRADING_HOURS_FILTER_V1", flush=True)
    print(
        "SESSION_SIDE_GATE_TRADING_HOURS_FILTER_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"min_hour_msk={min_hour}",
        f"max_hour_msk={max_hour}",
        f"total_kept={total_kept}",
        f"total_removed={total_removed}",
        f"source_path={SOURCE_PATH}",
        f"filtered_path={FILTERED_PATH}",
        f"backup_path={BACKUP_PATH}",
        flush=True,
    )
    print(
        "SESSION_SIDE_GATE_TRADING_HOURS_FILTER_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
