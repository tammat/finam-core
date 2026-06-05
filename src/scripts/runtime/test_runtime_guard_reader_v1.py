#!/usr/bin/env python3
from __future__ import annotations

from finam_core.governance.runtime_guard_reader import RuntimeGuardReader


def main():
    reader = RuntimeGuardReader()
    guards = reader.load_active_guards()

    block = sum(1 for g in guards.values() if g.decision == "BLOCK_STOP_DOMINATED")
    watch = sum(1 for g in guards.values() if g.decision == "WATCH_NEGATIVE_TOTAL")
    allow = sum(1 for g in guards.values() if g.decision == "ALLOW_WATCH")

    print("=== RUNTIME GUARD READER V1 ===")
    print(f"RUNTIME_GUARD_STATE_LOADED rows={len(guards)}")
    print(f"RUNTIME_GUARD_BLOCK_CANDIDATES rows={block}")
    print(f"RUNTIME_GUARD_WATCH rows={watch}")
    print(f"RUNTIME_GUARD_ALLOW rows={allow}")

    if len(guards) == 0:
        raise SystemExit("RUNTIME_GUARD_READER_EMPTY")

    print("VERDICT=OK")


if __name__ == "__main__":
    main()
