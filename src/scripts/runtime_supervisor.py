from __future__ import annotations

import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from finam_core.notifications.telegram_notifier import TelegramNotifier


SERVICES = [
    "finam-paper-runtime.service",
    "finam-governance.service",
    "finam-orchestrator-safe.service",
    "finam-projection-worker.service",
]

TIMERS = [
    "finam-radar-chain.timer",
    "signal-lifecycle-monitor.timer",
    "policy-rotation.timer",
    "finam-position-sync.timer",
    "finam-manual-reconciliation.timer",
]

LOGS = [
    "/opt/finam-core/logs/finam_radar_chain.log",
    "/opt/finam-core/logs/signal_lifecycle_monitor.log",
]


def run_cmd(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
    return p.returncode, (p.stdout + p.stderr).strip()


def is_active(unit: str) -> bool:
    code, out = run_cmd(["systemctl", "is-active", unit])
    return code == 0 and out.strip() == "active"


def log_age_minutes(path: str) -> float | None:
    p = Path(path)
    if not p.exists():
        return None
    mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime).total_seconds() / 60.0


def main() -> int:
    max_log_age_min = float(os.getenv("RUNTIME_SUPERVISOR_MAX_LOG_AGE_MIN", "30"))
    send_ok = os.getenv("RUNTIME_SUPERVISOR_SEND_OK", "0") == "1"

    problems: list[str] = []
    ok_lines: list[str] = []

    for unit in SERVICES:
        if is_active(unit):
            ok_lines.append(f"✅ service {unit}: active")
        else:
            problems.append(f"🛑 service {unit}: not active")

    for unit in TIMERS:
        if is_active(unit):
            ok_lines.append(f"✅ timer {unit}: active")
        else:
            problems.append(f"🛑 timer {unit}: not active")

    for log_path in LOGS:
        age = log_age_minutes(log_path)
        if age is None:
            problems.append(f"🛑 log missing: {log_path}")
            continue

        if age > max_log_age_min:
            problems.append(f"⚠️ stale log: {log_path}; age_min={age:.1f}")
        else:
            ok_lines.append(f"✅ log fresh: {log_path}; age_min={age:.1f}")

    status = "CRITICAL" if problems else "OK"

    text = (
        f"🧭 Runtime Supervisor\n\n"
        f"Статус: {status}\n"
        f"Проверено: {datetime.now(timezone.utc).isoformat()}\n\n"
    )

    if problems:
        text += "Проблемы:\n" + "\n".join(problems[:20])
    else:
        text += "Все ключевые сервисы и таймеры активны."

    print(text, flush=True)

    if problems or send_ok:
        TelegramNotifier().send(text)

    print(
        f"RUNTIME_SUPERVISOR_OK status={status} problems={len(problems)}",
        flush=True,
    )

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
