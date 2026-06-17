#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess


SERVICE = "finam-paper-pipeline.service"


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return proc.stdout or ""


def systemd_env() -> str:
    out = run(["systemctl", "show", SERVICE, "-p", "Environment", "--no-pager"])
    return out.replace("Environment=", "").replace(" ", "\n")


def main_pid() -> str:
    out = run(["systemctl", "show", SERVICE, "-p", "MainPID", "--no-pager"])
    return out.strip().replace("MainPID=", "")


def process_env(pid: str) -> str:
    path = f"/proc/{pid}/environ"

    # Русский комментарий:
    # /proc/<pid>/environ может быть закрыт для пользователя alex.
    # Читать файл должен именно sudo cat, а не shell-редирект от обычного пользователя.
    proc = subprocess.run(
        ["sudo", "cat", path],
        capture_output=True,
        check=False,
    )

    if proc.returncode == 0:
        return proc.stdout.replace(b"\x00", b"\n").decode("utf-8", errors="replace")

    try:
        raw = open(path, "rb").read()
        return raw.replace(b"\x00", b"\n").decode("utf-8", errors="replace")
    except Exception as exc:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        return (
            f"PROCESS_ENV_READ_ERROR={type(exc).__name__}:{exc}; "
            f"sudo_cat_rc={proc.returncode}; stderr={stderr}"
        )


def journal_lines(since: str = "60 minutes ago") -> list[str]:
    out = run(["journalctl", "-u", SERVICE, "--since", since, "--no-pager"])
    return out.splitlines()


def contains_env(env_text: str, key: str, expected: str | None = None) -> bool:
    for line in env_text.splitlines():
        if expected is None:
            if line.startswith(key + "="):
                return True
        else:
            if line.strip() == f"{key}={expected}":
                return True
    return False


def main() -> int:
    print("=== NGQ6 CLUSTER ADVISORY RUNTIME ENV AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    sd_env = systemd_env()
    pid = main_pid()
    proc_env = process_env(pid) if pid and pid != "0" else ""

    sd_bypass_enabled = contains_env(sd_env, "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1", "1")
    sd_symbols_line = next(
        (x for x in sd_env.splitlines() if x.startswith("PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS=")),
        "",
    )
    sd_ngq6_allowed = "NGQ6@RTSX" in sd_symbols_line

    proc_bypass_enabled = contains_env(proc_env, "ENABLE_PAPER_CLUSTER_BLOCK_BYPASS_V1", "1")
    proc_symbols_line = next(
        (x for x in proc_env.splitlines() if x.startswith("PAPER_CLUSTER_BLOCK_BYPASS_SYMBOLS=")),
        "",
    )
    proc_ngq6_allowed = "NGQ6@RTSX" in proc_symbols_line

    lines = journal_lines()

    ngq6_cluster_blocks = sum(
        1 for x in lines
        if "PIPE_CLUSTER_BLOCK" in x
        and "NGQ6@RTSX" in x
    )

    ngq6_cluster_advisory = sum(
        1 for x in lines
        if "PIPE_CLUSTER_BLOCK_ADVISORY_CONTINUE" in x
        and "symbol=NGQ6@RTSX" in x
    )

    br_cluster_advisory = sum(
        1 for x in lines
        if "PIPE_CLUSTER_BLOCK_ADVISORY_CONTINUE" in x
        and "symbol=BRN6@RTSX" in x
    )

    ngq6_trade_exec = sum(
        1 for x in lines
        if "PIPE_TRADE_EXEC symbol=NGQ6@RTSX" in x
    )

    ngq6_fills = sum(
        1 for x in lines
        if "PIPE_FILLED paper NGQ6@RTSX" in x
    )

    ngq6_after_portfolio = sum(
        1 for x in lines
        if "PIPE_NG_EXEC_TRACE_BEFORE_PORTFOLIO_GATE symbol=NGQ6@RTSX" in x
    )

    print(f"SERVICE={SERVICE}")
    print(f"MAIN_PID={pid}")

    print(f"SYSTEMD_BYPASS_ENABLED={int(sd_bypass_enabled)}")
    print(f"SYSTEMD_SYMBOLS_LINE={sd_symbols_line}")
    print(f"SYSTEMD_NGQ6_ALLOWED={int(sd_ngq6_allowed)}")

    print(f"PROCESS_BYPASS_ENABLED={int(proc_bypass_enabled)}")
    print(f"PROCESS_SYMBOLS_LINE={proc_symbols_line}")
    print(f"PROCESS_NGQ6_ALLOWED={int(proc_ngq6_allowed)}")

    print(f"LOG_NGQ6_AFTER_PORTFOLIO={ngq6_after_portfolio}")
    print(f"LOG_NGQ6_CLUSTER_BLOCKS={ngq6_cluster_blocks}")
    print(f"LOG_NGQ6_CLUSTER_ADVISORY={ngq6_cluster_advisory}")
    print(f"LOG_BR_CLUSTER_ADVISORY={br_cluster_advisory}")
    print(f"LOG_NGQ6_TRADE_EXEC={ngq6_trade_exec}")
    print(f"LOG_NGQ6_FILLS={ngq6_fills}")

    if not sd_bypass_enabled or not sd_ngq6_allowed:
        verdict = "SYSTEMD_ENV_NOT_CONFIGURED"
    elif not proc_bypass_enabled or not proc_ngq6_allowed:
        verdict = "ACTIVE_PROCESS_ENV_NOT_UPDATED_RESTART_REQUIRED"
    elif ngq6_after_portfolio > 0 and ngq6_cluster_advisory == 0:
        verdict = "NGQ6_ENV_OK_BUT_CLUSTER_ADVISORY_NOT_MATCHING"
    elif ngq6_cluster_advisory > 0 and ngq6_trade_exec == 0:
        verdict = "NGQ6_CLUSTER_ADVISORY_OK_NEXT_BLOCK_AFTER_CLUSTER"
    elif ngq6_trade_exec > 0 and ngq6_fills == 0:
        verdict = "NGQ6_TRADE_EXEC_WITHOUT_FILL"
    elif ngq6_fills > 0:
        verdict = "NGQ6_CLUSTER_ADVISORY_AND_FILL_OK"
    else:
        verdict = "WAITING_FOR_NEXT_NGQ6_CLUSTER_EVENT"

    print(f"VERDICT={verdict}")
    print("NGQ6_CLUSTER_ADVISORY_RUNTIME_ENV_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
