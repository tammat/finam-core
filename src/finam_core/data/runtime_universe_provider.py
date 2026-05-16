from __future__ import annotations

from typing import Any


class RuntimeUniverseProvider:
    """Русский комментарий: читает активный runtime-universe из dynamic_watchlist."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def load_symbols(
        self,
        source: str = "opportunity_scanner",
        limit: int = 10,
        sources: list[str] | None = None,
    ) -> list[str]:
        sources = sources or [source]

        sql = """
        select distinct on (symbol)
            symbol,
            priority,
            score,
            updated_at
        from dynamic_watchlist
        where source = any(%s)
          and is_active = true
          and strategy is not null
          and strategy <> ''
        order by symbol, priority desc nulls last, score desc nulls last, updated_at desc nulls last
        """

        outer_sql = f"""
        select symbol
        from ({sql}) q
        order by priority desc nulls last, score desc nulls last, updated_at desc nulls last
        limit %s
        """

        conn = getattr(self.pg_logger, "conn", None)

        if conn is None and hasattr(self.pg_logger, "_connect"):
            with self.pg_logger._connect() as runtime_conn:
                with runtime_conn.cursor() as cur:
                    cur.execute(outer_sql, (sources, int(limit)))
                    return [str(r[0]) for r in cur.fetchall()]

        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(outer_sql, (sources, int(limit)))
                return [str(r[0]) for r in cur.fetchall()]

        return []
