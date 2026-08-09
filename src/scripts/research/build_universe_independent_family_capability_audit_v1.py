#!/usr/bin/env python3
"""
UNIVERSE_INDEPENDENT_FAMILY_CAPABILITY_AUDIT_V1

Read-only inventory существующих research strategy families.

Цели:
- найти реально реализованные независимые family;
- показать конкретные файлы и строки;
- отделить уже проверенные базовые family:
  MOMENTUM / MEAN_REVERSION / BREAKOUT;
- не создавать новые strategy codes;
- не выполнять parameter search;
- не писать в PostgreSQL;
- не менять runtime/execution.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


ROOT = Path("/opt/finam-core")

SEARCH_ROOTS = (
    ROOT / "src/scripts",
    ROOT / "src/finam_core",
    ROOT / "src/marketcore",
    ROOT / "config/research",
)

FILE_SUFFIXES = {
    ".py",
    ".json",
    ".yaml",
    ".yml",
}

BASELINE_FAMILIES = {
    "MOMENTUM",
    "MEAN_REVERSION",
    "BREAKOUT",
}

INDEPENDENT_FAMILY_PATTERNS = {
    "TREND_PULLBACK": (
        "TREND_PULLBACK",
        "TREND PULLBACK",
        "pullback_atr",
    ),
    "RELATIVE_STRENGTH": (
        "RELATIVE_STRENGTH",
        "RELATIVE STRENGTH",
        "relative_strength",
    ),
    "INTERMARKET": (
        "INTERMARKET",
        "intermarket",
    ),
    "LEAD_LAG": (
        "LEAD_LAG",
        "LEAD LAG",
        "lead_lag",
    ),
    "VOLATILITY_STATE": (
        "VOLATILITY_STATE",
        "VOLATILITY STATE",
        "volatility_state",
    ),
    "REGIME": (
        "REGIME",
        "regime_code",
        "market_regime",
    ),
    "SESSION": (
        "SESSION",
        "session_code",
        "trading_session",
    ),
    "MEAN_REVERSION": (
        "MEAN_REVERSION",
        "MEAN REVERSION",
    ),
    "MOMENTUM": (
        "MOMENTUM",
    ),
    "BREAKOUT": (
        "BREAKOUT",
    ),
}


def relevant_files() -> list[Path]:
    files: list[Path] = []

    for base in SEARCH_ROOTS:
        if not base.exists():
            continue

        for path in base.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in FILE_SUFFIXES
                and "__pycache__" not in path.parts
            ):
                files.append(path)

    return sorted(set(files))


def main() -> int:
    print(
        "=== UNIVERSE INDEPENDENT FAMILY "
        "CAPABILITY AUDIT V1 ==="
    )
    print("mode=read_only_capability_audit")
    print("parameter_search_performed=0")
    print("strategy_created=0")
    print("db_writes_performed=0")
    print()

    family_hits: dict[
        str,
        list[tuple[Path, int, str]],
    ] = defaultdict(list)

    for path in relevant_files():
        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError:
            continue

        for line_no, line in enumerate(
            lines,
            start=1,
        ):
            upper = line.upper()

            for family, patterns in (
                INDEPENDENT_FAMILY_PATTERNS.items()
            ):
                matched = False

                for pattern in patterns:
                    if pattern.upper() in upper:
                        matched = True
                        break

                if not matched:
                    continue

                family_hits[family].append(
                    (
                        path.relative_to(ROOT),
                        line_no,
                        " ".join(line.split()),
                    )
                )

    all_families = sorted(
        family_hits.keys()
    )

    independent_families = [
        family
        for family in all_families
        if family not in BASELINE_FAMILIES
    ]

    print("FAMILY_SUMMARY_ROWS")

    for family in all_families:
        hits = family_hits[family]

        unique_files = sorted({
            str(path)
            for path, _, _ in hits
        })

        category = (
            "BASELINE_ALREADY_TESTED"
            if family in BASELINE_FAMILIES
            else "INDEPENDENT_CANDIDATE"
        )

        print(
            "FAMILY_SUMMARY_ROW "
            f"family={family} "
            f"category={category} "
            f"files={len(unique_files)} "
            f"hits={len(hits)}"
        )

    print()
    print("CAPABILITY_ROWS")

    for family in all_families:
        # Ограничиваем вывод, но сохраняем разнообразие файлов.
        emitted = 0
        seen_paths: set[str] = set()

        for path, line_no, text in family_hits[family]:
            path_text = str(path)

            # Вначале показываем хотя бы по одной строке
            # из разных файлов.
            if (
                path_text in seen_paths
                and emitted >= 12
            ):
                continue

            seen_paths.add(path_text)

            print(
                "CAPABILITY_ROW "
                f"family={family} "
                f"path={path_text} "
                f"line={line_no} "
                f"text={text}"
            )

            emitted += 1

            if emitted >= 20:
                break

    print()
    print("INDEPENDENT_FAMILY_ROWS")

    for family in independent_families:
        paths = sorted({
            str(path)
            for path, _, _ in family_hits[family]
        })

        print(
            "INDEPENDENT_FAMILY_ROW "
            f"family={family} "
            f"evidence_files={len(paths)} "
            f"first_path="
            f"{paths[0] if paths else 'NONE'}"
        )

    print()
    print(
        "SUMMARY_ROW "
        f"families_found={len(all_families)} "
        f"baseline_families="
        f"{sum(
            1
            for family in all_families
            if family in BASELINE_FAMILIES
        )} "
        f"independent_families="
        f"{len(independent_families)}"
    )

    print(
        "independent_family_names="
        + (
            ",".join(independent_families)
            if independent_families
            else "NONE"
        )
    )

    print("parameter_search_performed=0")
    print("strategy_created=0")
    print("economic_edge_claimed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "UNIVERSE_INDEPENDENT_FAMILY_"
        "CAPABILITY_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
