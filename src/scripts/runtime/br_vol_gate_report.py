from __future__ import annotations

import argparse
import re
import subprocess
from statistics import mean


PATTERN = re.compile(
    r"(PIPE_VOL_LOW_BLOCK|PIPE_VOL_GATE_OK).*?"
    r"atr_pct=(?P<atr_pct>[0-9.]+).*?"
    r"threshold=(?P<threshold>[0-9.]+).*?"
    r"static_threshold=(?P<static_threshold>[0-9.]+).*?"
    r"mode=(?P<mode>[a-zA-Z0-9_]+).*?"
    r"reason=(?P<reason>[a-zA-Z0-9_]+).*?"
    r"atr=(?P<atr>[0-9.]+).*?"
    r"price=(?P<price>[0-9.]+)"
)


def run_journalctl(since: str, unit: str) -> str:
    cmd = ["journalctl", "-u", unit, "--since", since, "--no-pager", "-l"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.stdout or ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="today")
    parser.add_argument("--unit", default="finam-core")
    args = parser.parse_args()

    text = run_journalctl(args.since, args.unit)

    rows = []
    for line in text.splitlines():
        match = PATTERN.search(line)
        if not match:
            continue

        event = "PIPE_VOL_GATE_OK" if "PIPE_VOL_GATE_OK" in line else "PIPE_VOL_LOW_BLOCK"
        row = {
            "event": event,
            "atr_pct": float(match.group("atr_pct")),
            "threshold": float(match.group("threshold")),
            "static_threshold": float(match.group("static_threshold")),
            "mode": match.group("mode"),
            "reason": match.group("reason"),
            "atr": float(match.group("atr")),
            "price": float(match.group("price")),
        }
        rows.append(row)

    total = len(rows)
    ok = sum(1 for r in rows if r["event"] == "PIPE_VOL_GATE_OK")
    blocked = sum(1 for r in rows if r["event"] == "PIPE_VOL_LOW_BLOCK")

    print(f"BR_VOL_GATE_REPORT since={args.since} rows={total} ok={ok} blocked={blocked}")

    if not rows:
        return 0

    atr_values = [r["atr_pct"] for r in rows]
    threshold_values = [r["threshold"] for r in rows]

    print(
        "BR_VOL_GATE_SUMMARY",
        f"avg_atr_pct={mean(atr_values):.6f}",
        f"min_atr_pct={min(atr_values):.6f}",
        f"max_atr_pct={max(atr_values):.6f}",
        f"avg_threshold={mean(threshold_values):.6f}",
        f"min_threshold={min(threshold_values):.6f}",
        f"max_threshold={max(threshold_values):.6f}",
    )

    by_mode: dict[str, dict[str, int]] = {}
    for r in rows:
        mode = r["mode"]
        by_mode.setdefault(mode, {"ok": 0, "blocked": 0})
        if r["event"] == "PIPE_VOL_GATE_OK":
            by_mode[mode]["ok"] += 1
        else:
            by_mode[mode]["blocked"] += 1

    for mode, stat in sorted(by_mode.items()):
        print(
            "BR_VOL_GATE_MODE",
            f"mode={mode}",
            f"ok={stat['ok']}",
            f"blocked={stat['blocked']}",
        )

    last = rows[-1]
    print(
        "BR_VOL_GATE_LAST",
        f"event={last['event']}",
        f"atr_pct={last['atr_pct']:.6f}",
        f"threshold={last['threshold']:.6f}",
        f"mode={last['mode']}",
        f"reason={last['reason']}",
        f"price={last['price']:.4f}",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
