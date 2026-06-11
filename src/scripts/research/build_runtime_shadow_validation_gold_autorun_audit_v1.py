#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import subprocess

SERVICE = Path("infra/finam-gold-shadow-validation.service")
TIMER = Path("infra/finam-gold-shadow-validation.timer")

FORBIDDEN = [
    "runtime_allow=1",
    "execution_enabled=1",
    "send_order",
    "place_order",
    "create_order",
    "real_execution",
]

def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return r.stdout.strip()

def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD AUTORUN AUDIT V1 ===")
    print("mode=autorun_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    service_text = SERVICE.read_text() if SERVICE.exists() else ""
    timer_text = TIMER.read_text() if TIMER.exists() else ""

    forbidden_hits = [
        x for x in FORBIDDEN
        if x.lower() in (service_text + "\n" + timer_text).lower()
    ]

    service_ok = (
        SERVICE.exists()
        and "GOLD_SYMBOL=GDU6@RTSX" in service_text
        and "build_runtime_shadow_validation_gold_v1.py" in service_text
        and "NoNewPrivileges=true" in service_text
    )

    timer_ok = (
        TIMER.exists()
        and "finam-gold-shadow-validation.service" in timer_text
        and "15..18" in timer_text
        and "Europe/Moscow" in timer_text
    )

    systemd_timer_status = run(["systemctl", "is-enabled", "finam-gold-shadow-validation.timer"])
    systemd_timer_active = run(["systemctl", "is-active", "finam-gold-shadow-validation.timer"])
    list_timers = run(["systemctl", "list-timers", "--all", "finam-gold-shadow-validation.timer", "--no-pager"])

    print(
        "AUDIT_ROW "
        f"service_file_exists={int(SERVICE.exists())} "
        f"timer_file_exists={int(TIMER.exists())} "
        f"service_ok={int(service_ok)} "
        f"timer_ok={int(timer_ok)} "
        f"forbidden_hits={len(forbidden_hits)} "
        f"forbidden={','.join(forbidden_hits) if forbidden_hits else 'none'}"
    )

    print(
        "SYSTEMD_ROW "
        f"timer_enabled={systemd_timer_status} "
        f"timer_active={systemd_timer_active}"
    )

    print("NEXT_TIMER_ROWS")
    for line in list_timers.splitlines():
        if "finam-gold-shadow-validation" in line:
            print(f"NEXT_TIMER_ROW {line}")

    verdict = "PASS" if (
        service_ok
        and timer_ok
        and not forbidden_hits
        and systemd_timer_status == "enabled"
        and systemd_timer_active == "active"
    ) else "FAIL"

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        raise SystemExit(1)

    print("RUNTIME_SHADOW_VALIDATION_GOLD_AUTORUN_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
