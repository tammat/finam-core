from __future__ import annotations

import psycopg


class InstrumentDisplayNameResolver:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def resolve(self, symbol: str) -> str:
        value = str(symbol).strip().upper()
        return (
            self._from_real_position_snapshots(value)
            or self._from_runtime_active_universe(value)
            or value
        )

    def _from_real_position_snapshots(self, symbol: str) -> str | None:
        base = symbol.split("@", 1)[0]

        sql = """
        SELECT COALESCE(
            raw_json->'raw'->>'short_name',
            raw_json->'raw'->>'display_name',
            raw_json->'raw'->>'name',
            raw_json->>'short_name',
            raw_json->>'display_name',
            raw_json->>'name',
            raw_json->'raw'->>'symbol'
        )
        FROM real_position_snapshots
        WHERE UPPER(symbol) = %s OR UPPER(symbol) = %s
        ORDER BY ts DESC, id DESC
        LIMIT 1
        """

        return self._scalar(sql, base, symbol)

    def _from_runtime_active_universe(self, symbol: str) -> str | None:
        sql = """
        SELECT display_name
        FROM runtime_active_universe
        WHERE UPPER(symbol) = %s
        ORDER BY updated_at DESC NULLS LAST
        LIMIT 1
        """

        return self._scalar(sql, symbol)

    def _scalar(self, sql: str, *params: str) -> str | None:
        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    row = cur.fetchone()
        except Exception:
            return None

        if not row or row[0] is None:
            return None

        value = str(row[0]).strip()
        return value or None
