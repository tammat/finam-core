from __future__ import annotations

from pathlib import Path

ROOTS = [
    Path("src/marketcore"),
    Path("src/scripts/build_edge_sprint_plan_from_recommendation_v1.py"),
]

TRADE_HARDCODE_TERMS = [
    "SBER@MISX",
    "LKOH@MISX",
    "BR@RTSX",
    "NG@RTSX",
    "VWAP_REVERSION_V1",
    "BOLLINGER_REVERSION_V1",
    "RSI_MEAN_REVERSION_V1",
]

EXCLUDE_PARTS = {
    "__pycache__",
    "dto",
    "presentation",
    "ui",
    "finam_proto",
}

EXCLUDE_NAME_PARTS = (
    "_plan_",
    "_audit_",
    "_diagnostic_",
    "_healthcheck_",
    "_validation_",
    "_probe_",
    "_dry_run",
    "_smoke",
    "_scorecard",
    "_report",
    "_review",
    "_trace",
)

ALLOWED_FILES = {
    "src/scripts/check_no_hardcode_v1.py",
    "src/scripts/build_edge_sprint_plan_from_recommendation_v1.py",
}

REPORT = Path("reports/no_hardcode_v1_latest.txt")


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in ROOTS:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".py":
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.py"))
    return files


def should_skip(path: Path) -> bool:
    path_str = str(path)

    if path_str in ALLOWED_FILES:
        return True

    if any(part in EXCLUDE_PARTS for part in path.parts):
        return True

    if any(name_part in path.name for name_part in EXCLUDE_NAME_PARTS):
        return True

    return False


def main() -> None:
    findings: list[str] = []

    for path in iter_python_files():
        if should_skip(path):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")

        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            for term in TRADE_HARDCODE_TERMS:
                if term in line:
                    findings.append(f"{path}:{lineno}: {term}: {stripped}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    verdict = "NO_HARDCODE_V1_READY" if not findings else "NO_HARDCODE_V1_FAILED"

    lines = [
        "=== NO_HARDCODE_V1 ===",
        "policy=production_trade_hardcode_only",
        f"findings={len(findings)}",
        "",
        "--- FINDINGS ---",
        *findings,
        f"VERDICT={verdict}",
    ]

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
