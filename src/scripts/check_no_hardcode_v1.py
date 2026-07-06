from __future__ import annotations

from pathlib import Path

ROOTS = [
    Path("src/marketcore"),
]

EXCLUDE_PARTS = {
    "__pycache__",
    "dto",
}

POLICY = Path("config/no_hardcode_policy_v1.txt")
REPORT = Path("reports/no_hardcode_v1_latest.txt")


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_PARTS for part in path.parts)


def main() -> None:
    terms = [
        line.strip()
        for line in POLICY.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    findings: list[str] = []

    for root in ROOTS:
        for path in root.rglob("*.py"):
            if should_skip(path):
                continue

            text = path.read_text(encoding="utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), start=1):
                for term in terms:
                    if term in line:
                        findings.append(f"{path}:{lineno}: {term}: {line.strip()}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "=== NO_HARDCODE_V1 ===",
        f"findings={len(findings)}",
        "",
        "--- FINDINGS ---",
        *findings,
    ]

    if findings:
        lines.append("VERDICT=NO_HARDCODE_V1_FAILED")
    else:
        lines.append("VERDICT=NO_HARDCODE_V1_READY")

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    if findings:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
