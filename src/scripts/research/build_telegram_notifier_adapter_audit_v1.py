#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path("/opt/finam-core")

SEARCH_DIRS = [
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "infra",
]

TERMS = [
    "Telegram",
    "telegram",
    "TELEGRAM",
    "send_message",
    "bot_token",
    "chat_id",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "NOTIFIER",
    "notify",
    "Notification",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def iter_python_and_shell_files() -> list[Path]:
    files: list[Path] = []
    for base in SEARCH_DIRS:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix in {".py", ".sh", ".service", ".env", ".txt", ".md"}:
                files.append(path)
    return files


def main() -> int:
    print("=== TELEGRAM NOTIFIER ADAPTER AUDIT V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print("telegram_send=0")
    print("audit_scope=source_only")

    hits: list[tuple[str, int, str, str]] = []

    for path in iter_python_and_shell_files():
        rel = str(path.relative_to(ROOT))
        text = read_text(path)
        if not text:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            for term in TERMS:
                if term in line:
                    hits.append((rel, line_no, term, line.strip()))
                    break

    print()
    print("TELEGRAM_NOTIFIER_SOURCE_HITS")
    for rel, line_no, term, code in hits:
        safe_code = re.sub(r"(token|TOKEN|password|PASSWORD|secret|SECRET)=([^ ]+)", r"\1=***", code)
        print(
            "TELEGRAM_NOTIFIER_SOURCE_HIT "
            f"file={rel} line={line_no} term={term} code={safe_code}"
        )

    files_with_hits = sorted(set(rel for rel, *_ in hits))
    py_hits = [h for h in hits if h[0].endswith(".py")]
    send_message_hits = [h for h in hits if "send_message" in h[3]]
    token_hits = [h for h in hits if "TOKEN" in h[3].upper() or "bot_token" in h[3]]
    chat_hits = [h for h in hits if "CHAT" in h[3].upper() or "chat_id" in h[3]]
    notifier_class_hits = [
        h for h in hits
        if "class " in h[3] and ("Telegram" in h[3] or "Notifier" in h[3] or "Notification" in h[3])
    ]

    env_keys = []
    for key in sorted(os.environ):
        if "TELEGRAM" in key.upper() or "TG_" in key.upper():
            value_state = "SET" if os.environ.get(key) else "EMPTY"
            env_keys.append((key, value_state))

    print()
    print("TELEGRAM_NOTIFIER_ENV_ROWS")
    if not env_keys:
        print("TELEGRAM_NOTIFIER_ENV_ROW status=NO_TELEGRAM_ENV_KEYS_VISIBLE")
    for key, state in env_keys:
        print(f"TELEGRAM_NOTIFIER_ENV_ROW key={key} state={state}")

    print()
    print("TELEGRAM_NOTIFIER_ADAPTER_AUDIT_SUMMARY")
    print(f"files_with_hits={len(files_with_hits)}")
    print(f"hits_total={len(hits)}")
    print(f"python_hits={len(py_hits)}")
    print(f"send_message_hits={len(send_message_hits)}")
    print(f"token_hits={len(token_hits)}")
    print(f"chat_hits={len(chat_hits)}")
    print(f"notifier_class_hits={len(notifier_class_hits)}")
    print(f"telegram_env_keys={len(env_keys)}")
    print("db_update=0")
    print("telegram_send=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if send_message_hits and (token_hits or env_keys):
        print("VERDICT=TELEGRAM_NOTIFIER_ADAPTER_FOUND")
    elif hits:
        print("VERDICT=TELEGRAM_NOTIFIER_REFERENCES_FOUND_REVIEW_REQUIRED")
    else:
        print("VERDICT=TELEGRAM_NOTIFIER_ADAPTER_NOT_FOUND")

    print("TELEGRAM_NOTIFIER_ADAPTER_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
