# -*- coding: utf-8 -*-
"""
Инициализация PostgreSQL-схемы Finam_Core.
SQLite не используется.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg


def get_dsn() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "finam")
    user = os.getenv("DB_USER", "finam")
    password = os.getenv("DB_PASSWORD", "finam")

    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    migration_file = root / "finam_core" / "storage" / "migrations.sql"

    if not migration_file.exists():
        print(f"ERROR: migration file not found: {migration_file}", file=sys.stderr)
        return 1

    sql = migration_file.read_text(encoding="utf-8")

    try:
        with psycopg.connect(get_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

        print("OK: PostgreSQL schema initialized")
        print(f"MIGRATION: {migration_file}")
        return 0

    except Exception as exc:
        print(f"ERROR: PostgreSQL init failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
