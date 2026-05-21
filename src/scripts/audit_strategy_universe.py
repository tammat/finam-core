from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(".")
REPORT = Path("reports/strategy_universe_audit.md")

PATTERNS = {
    "strategy_files": [
        "strategy",
        "br_conservative",
        "ng_volatility",
        "mean_reversion",
        "breakout",
        "signal_router",
        "strategy_runtime",
    ],
    "runtime_universe": [
        "runtime_active_universe",
        "active_universe",
        "runtime_universe",
        "watchlist",
        "dynamic_watchlist",
    ],
    "symbol_strategy_mapping": [
        "strategy_by_symbol",
        "strategy_map",
        "map_symbol_to_strategy",
        "BRM6@RTSX",
        "SBER@MISX",
        "NG",
    ],
    "analytics_integration": [
        "analytics_exit_policy_selected",
        "ExitPolicyAdvisor",
        "incremental_exit",
        "analytics_runtime_supervisor",
    ],
}


def iter_source_files() -> list[Path]:
    result: list[Path] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        if any(part in {".git", "venv", ".venv", "__pycache__"} for part in path.parts):
            continue

        if path.suffix not in {".py", ".sh", ".sql", ".md", ".yml", ".yaml", ".json"}:
            continue

        result.append(path)

    return sorted(result)


def grep_files(files: list[Path], needles: list[str]) -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []

    for path in files:
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            normalized = line.lower()
            if any(needle.lower() in normalized for needle in needles):
                found.append((str(path), lineno, line.strip()))

    return found


def find_classes(files: list[Path]) -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []

    pattern = re.compile(r"^\s*class\s+([A-Za-z0-9_]*(Strategy|Runtime|Universe|Advisor|Router|Resolver|Mapper)[A-Za-z0-9_]*)")

    for path in files:
        if path.suffix != ".py":
            continue

        try:
            lines = path.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        for lineno, line in enumerate(lines, start=1):
            if pattern.search(line):
                found.append((str(path), lineno, line.strip()))

    return found


def main() -> int:
    files = iter_source_files()

    REPORT.parent.mkdir(parents=True, exist_ok=True)

    sections: list[str] = []
    sections.append("# Strategy / Runtime Universe Audit\n")
    sections.append("## 1. Область аудита\n")
    sections.append(f"Просканировано файлов: `{len(files)}`\n")

    sections.append("## 2. Найденные классы Strategy/Runtime/Universe/Advisor\n")
    classes = find_classes(files)
    if classes:
        for path, lineno, line in classes:
            sections.append(f"- `{path}:{lineno}` — `{line}`")
    else:
        sections.append("- Не найдено")
    sections.append("")

    for title, needles in PATTERNS.items():
        sections.append(f"## 3. {title}\n")
        rows = grep_files(files, needles)

        if not rows:
            sections.append("- Не найдено\n")
            continue

        for path, lineno, line in rows[:250]:
            sections.append(f"- `{path}:{lineno}` — `{line}`")

        if len(rows) > 250:
            sections.append(f"- ... обрезано, всего совпадений: `{len(rows)}`")

        sections.append("")

    sections.append("## 4. Предварительный вывод\n")
    sections.append(
        "- Этот отчёт нужен, чтобы определить существующий source of truth для `symbol → strategy`."
    )
    sections.append(
        "- Новый registry не должен дублировать уже существующие runtime/universe/control таблицы."
    )
    sections.append(
        "- Следующий шаг: вручную классифицировать найденные источники как primary / secondary / legacy / test-only."
    )

    REPORT.write_text("\n".join(sections))

    print(f"AUDIT_STRATEGY_UNIVERSE_OK report={REPORT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
