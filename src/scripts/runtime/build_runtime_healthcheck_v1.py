from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class LogStats:
    tracebacks: int
    errors: int
    vol_low_blocks: int
    vol_gate_ok: int
    compression_watch: int
    short_only_blocks: int
    paper_executes: int
    regime_lines: int


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout or "", result.stderr or ""


def read_journal(unit: str, since: str) -> str:
    code, out, err = run_cmd(["journalctl", "-u", unit, "--since", since, "--no-pager", "-l"])
    if code != 0:
        return err or out
    return out


def service_active(unit: str) -> bool:
    code, out, _ = run_cmd(["systemctl", "is-active", unit])
    return code == 0 and out.strip() == "active"


def count_logs(text: str) -> LogStats:
    return LogStats(
        tracebacks=text.count("Traceback"),
        errors=len(re.findall(r"\bERROR\b|Exception|FAILED|failed", text)),
        vol_low_blocks=text.count("PIPE_VOL_LOW_BLOCK"),
        vol_gate_ok=text.count("PIPE_VOL_GATE_OK"),
        compression_watch=text.count("PIPE_BR_COMPRESSION_WATCH"),
        short_only_blocks=text.count("PIPE_BR_SHORT_ONLY_BLOCK"),
        paper_executes=text.count("PAPER_EXECUTE"),
        regime_lines=len(re.findall(r"\bREGIME\b", text)),
    )


def extract_last_price(text: str) -> str:
    matches = re.findall(r"price=([0-9.]+)", text)
    return matches[-1] if matches else "NA"


def classify(stats: LogStats, active: bool) -> tuple[str, str]:
    if not active:
        return "HEALTH_DEGRADED", "systemd_service_not_active"

    if stats.tracebacks > 0:
        return "HEALTH_DEGRADED", "traceback_detected"

    if stats.errors > 0:
        return "HEALTH_WARN", "errors_detected"

    if stats.vol_low_blocks > 0 and stats.compression_watch > 0 and stats.paper_executes == 0:
        return "HEALTHY_IDLE_COMPRESSION", "market_compression_no_trade_environment"

    if stats.vol_gate_ok > 0 and stats.paper_executes == 0:
        return "HEALTHY_WAITING_FOR_EXECUTION_SIGNAL", "vol_gate_passed_no_execution_yet"

    if stats.paper_executes > 0:
        return "HEALTHY_ACTIVE_TRADING", "paper_execution_detected"

    if stats.regime_lines > 0:
        return "HEALTHY_IDLE", "runtime_alive_no_trade"

    return "HEALTH_WARN", "no_runtime_activity_detected"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit", default="finam-core")
    parser.add_argument("--since", default="30 minutes ago")
    args = parser.parse_args()

    active = service_active(args.unit)
    logs = read_journal(args.unit, args.since)
    stats = count_logs(logs)
    verdict, reason = classify(stats, active)

    print("FINAM_CORE_RUNTIME_HEALTHCHECK_V1")
    print(f"generated_at={datetime.now(timezone.utc).isoformat()}")
    print(f"unit={args.unit}")
    print(f"since={args.since}")

    print("SYSTEM")
    print(f"systemd_active={str(active).lower()}")
    print(f"tracebacks={stats.tracebacks}")
    print(f"errors={stats.errors}")

    print("PIPELINE")
    print(f"regime_lines={stats.regime_lines}")
    print(f"vol_low_blocks={stats.vol_low_blocks}")
    print(f"vol_gate_ok={stats.vol_gate_ok}")
    print(f"compression_watch={stats.compression_watch}")
    print(f"short_only_blocks={stats.short_only_blocks}")
    print(f"paper_executes={stats.paper_executes}")
    print(f"last_price={extract_last_price(logs)}")

    print("SUMMARY")
    print(f"runtime_health={verdict}")
    print(f"reason={reason}")
    print(f"FINAM_CORE_RUNTIME_HEALTHCHECK_V1_OK status={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
