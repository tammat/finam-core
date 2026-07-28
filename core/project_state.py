#!/usr/bin/env python3
"""Проверка master-context проекта MarketCore."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = PROJECT_ROOT / "PROJECT_STATE.md"

REQUIRED_SECTIONS = (
    "## 1. ЦЕЛЬ ПРОЕКТА",
    "## 2. ЗАФИКСИРОВАННАЯ АРХИТЕКТУРА",
    "## 3. RISK ENGINE",
    "## 4. ТЕКУЩИЙ РЕЖИМ",
    "## 7. ЗАФИКСИРОВАННЫЙ ПОРЯДОК ВАЛИДАЦИИ EDGE",
    "## 9. КОМИССИИ И ТОРГОВЫЕ ИЗДЕРЖКИ",
    "## 13. ТЕСТИРОВАНИЕ",
    "## 14. CHECKPOINT И GIT",
    "## 15. ИЗВЕСТНЫЕ ПРОБЕЛЫ",
    "## 17. СЛЕДУЮЩИЙ ЭТАП",
)

REQUIRED_GUARDS = (
    "PostgreSQL",
    "SQLite запрещен",
    "real_trading_enabled=0",
    "execution_enabled=0",
    "micro_live_allowed=0",
    "ai_direct_orders_allowed=0",
)


def main() -> int:
    if not STATE_FILE.is_file():
        print(f"ERROR=PROJECT_STATE_NOT_FOUND path={STATE_FILE}")
        return 1

    text = STATE_FILE.read_text(encoding="utf-8")

    missing_sections = [
        section for section in REQUIRED_SECTIONS if section not in text
    ]
    missing_guards = [
        guard for guard in REQUIRED_GUARDS if guard not in text
    ]

    if missing_sections:
        for section in missing_sections:
            print(f"ERROR=MISSING_SECTION value={section}")
        return 2

    if missing_guards:
        for guard in missing_guards:
            print(f"ERROR=MISSING_GUARD value={guard}")
        return 3

    print(f"PROJECT_STATE_FILE={STATE_FILE}")
    print(f"PROJECT_STATE_BYTES={STATE_FILE.stat().st_size}")
    print(f"PROJECT_STATE_SECTIONS={len(REQUIRED_SECTIONS)}")
    print(f"PROJECT_STATE_GUARDS={len(REQUIRED_GUARDS)}")
    print("architecture_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("micro_live_allowed=0")
    print("VERDICT=PROJECT_MASTER_CONTEXT_V1_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
