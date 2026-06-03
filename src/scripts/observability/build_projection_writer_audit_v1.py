#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path


ROOTS = [
    Path("src/finam_core"),
    Path("src/scripts"),
]


PATTERNS = [
    "ProjectionStore",
    "projection_store",
    "position_projection",
    "publish({\"type\": \"FILL\"",
    "publish({'type': 'FILL'",
    "subscribe",
    "on_fill",
]


def main() -> int:
    print("=== PROJECTION WRITER AUDIT V1 ===")
    print()

    found = {p: [] for p in PATTERNS}

    for root in ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue

            for pattern in PATTERNS:
                if pattern in text:
                    lines = []
                    for i, line in enumerate(text.splitlines(), start=1):
                        if pattern in line:
                            lines.append((i, line.strip()))
                    found[pattern].append((path, lines[:10]))

    for pattern in PATTERNS:
        print(f"PATTERN={pattern}")
        items = found[pattern]
        if not items:
            print("  NOT_FOUND")
            print()
            continue

        for path, lines in items[:20]:
            print(f"  {path}")
            for line_no, line in lines:
                print(f"    {line_no}: {line}")
        print()

    has_projection_store = bool(found["ProjectionStore"])
    has_projection_table_writer = bool(found["position_projection"])
    has_fill_publish = bool(found["publish({\"type\": \"FILL\""] or found["publish({'type': 'FILL'"])

    print("SUMMARY")
    print(f"has_projection_store={has_projection_store}")
    print(f"has_projection_table_writer={has_projection_table_writer}")
    print(f"has_fill_publish={has_fill_publish}")

    if has_projection_store and has_fill_publish:
        print("verdict=CHECK_WIRING")
        print("reason=writer_exists_and_fills_are_published_but_position_projection_is_empty")
    else:
        print("verdict=INCOMPLETE_PROJECTION_LAYER")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
