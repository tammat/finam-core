from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class RuntimeConfigValue:
    key: str
    value: str
    value_type: str
    source: str


class RuntimeConfig:
    """Русский комментарий: единая точка чтения production-critical параметров."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "")
        self._cache: dict[str, RuntimeConfigValue] = {}

    def get(self, key: str, default: str = "") -> str:
        if key in os.environ:
            return os.environ[key]

        item = self._get_from_db(key)
        if item is not None:
            return item.value

        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, "1" if default else "0").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key, str(default))
        try:
            return int(value)
        except ValueError:
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.get(key, str(default))
        try:
            return float(value)
        except ValueError:
            return default

    def _get_from_db(self, key: str) -> RuntimeConfigValue | None:
        if key in self._cache:
            return self._cache[key]

        if not self.database_url:
            return None

        sql = """
        SELECT key, value, value_type
        FROM runtime_config
        WHERE key = %s
        LIMIT 1;
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (key,))
                    row = cur.fetchone()
        except Exception:
            return None

        if row is None:
            return None

        item = RuntimeConfigValue(
            key=str(row[0]),
            value=str(row[1]),
            value_type=str(row[2]),
            source="runtime_config",
        )
        self._cache[key] = item
        return item
