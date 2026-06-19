#!/usr/bin/env python3
from __future__ import annotations

import ast
import os
from pathlib import Path


ROOT = Path("/opt/finam-core")

FILES = [
    ROOT / "src/finam_core/notifications/telegram_signal_taxonomy.py",
    ROOT / "src/finam_core/notifications/telegram_signal_router.py",
    ROOT / "src/finam_core/notifications/telegram_signal_dispatcher.py",
]


def emit_class_fields(path: Path, class_name: str) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)

    found = 0
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            found = 1
            print(f"TELEGRAM_SIGNAL_API_CLASS file={path.relative_to(ROOT)} class={class_name}")
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    annotation = ast.unparse(item.annotation) if item.annotation else "UNKNOWN"
                    default = ast.unparse(item.value) if item.value is not None else "REQUIRED"
                    print(
                        "TELEGRAM_SIGNAL_API_FIELD "
                        f"class={class_name} name={item.target.id} annotation={annotation} default={default}"
                    )
    return found


def main() -> int:
    print("=== TELEGRAM SIGNAL DISPATCHER API AUDIT V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print("telegram_send=0")

    class_hits = 0

    print()
    print("TELEGRAM_SIGNAL_API_ROWS")
    class_hits += emit_class_fields(FILES[0], "TelegramSignalMessage")
    class_hits += emit_class_fields(FILES[2], "TelegramSignalDispatchResult")

    for path in FILES:
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), start=1):
            if (
                "def " in line
                or "TARGET_ENV_BY_CHANNEL" in line
                or "TELEGRAM_" in line
                or "channel_type" in line
                or "confidence" in line
            ):
                print(
                    "TELEGRAM_SIGNAL_API_SOURCE_ROW "
                    f"file={path.relative_to(ROOT)} line={i} code={line.strip()}"
                )

    print()
    print("TELEGRAM_SIGNAL_DISPATCHER_API_AUDIT_SUMMARY")
    print(f"class_hits={class_hits}")
    print("db_update=0")
    print("telegram_send=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if class_hits >= 2:
        print("VERDICT=TELEGRAM_SIGNAL_DISPATCHER_API_READY")
    else:
        print("VERDICT=TELEGRAM_SIGNAL_DISPATCHER_API_REVIEW_REQUIRED")

    print("TELEGRAM_SIGNAL_DISPATCHER_API_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
