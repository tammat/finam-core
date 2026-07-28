from __future__ import annotations

from typing import Any


class RuntimeUniverseProvider:
    """Русский комментарий: читает активный runtime-universe из runtime_active_universe с fallback на dynamic_watchlist."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def load_symbols(
        self,
        source: str = "opportunity_scanner",
        limit: int = 10,
        sources: list[str] | None = None,
    ) -> list[str]:
        sources = sources or [source]

        active_sql = """
        select u.symbol
        from runtime_active_universe u
        left join analytics.hierarchical_runtime_priority_v1 h
          on h.symbol = u.symbol
        where u.is_enabled = true
          and u.strategy is not null
          and u.strategy <> ''
          and u.strategy <> 'NO_TRADE'
          and not exists (
              select 1
              from analytics.fresh_v4_early_loss_quarantine_v1 q
              where q.symbol = u.symbol
                and q.strategy_code = u.strategy
                and q.quarantined = true
                and not exists (
                    select 1
                    from analytics.fresh_v4_early_loss_quarantine_v1 viable
                    where viable.symbol = q.symbol
                      and viable.strategy_code = q.strategy_code
                      and viable.quarantined = false
                )
          )
        order by
          (h.symbol is not null) desc,
          h.priority_score desc nulls last,
          u.priority desc nulls last,
          u.score desc nulls last,
          u.updated_at desc nulls last
        limit %s
        """

        fallback_sql = """
        select symbol
        from (
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
              and strategy <> 'NO_TRADE'
            order by symbol, priority desc nulls last, score desc nulls last, updated_at desc nulls last
        ) q
        order by priority desc nulls last, score desc nulls last, updated_at desc nulls last
        limit %s
        """

        conn = getattr(self.pg_logger, "conn", None)

        if conn is None and hasattr(self.pg_logger, "_connect"):
            with self.pg_logger._connect() as runtime_conn:
                with runtime_conn.cursor() as cur:
                    cur.execute(active_sql, (int(limit),))
                    active_symbols = [str(r[0]) for r in cur.fetchall()]
                    if active_symbols:
                        return active_symbols

                    cur.execute(fallback_sql, (sources, int(limit)))
                    return [str(r[0]) for r in cur.fetchall()]

        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(active_sql, (int(limit),))
                active_symbols = [str(r[0]) for r in cur.fetchall()]
                if active_symbols:
                    return active_symbols

                cur.execute(fallback_sql, (sources, int(limit)))
                return [str(r[0]) for r in cur.fetchall()]

        return []
