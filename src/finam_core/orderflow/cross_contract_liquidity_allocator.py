from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ContractLiquidityDecision:
    continuous_symbol: str
    preferred_symbol: str
    score: float
    reason: str
    candidates: list[str]


class CrossContractLiquidityAllocator:
    """Русский комментарий: выбирает наиболее ликвидный/активный контракт внутри continuous group."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def choose_brent(self) -> ContractLiquidityDecision | None:
        return self.choose(
            continuous_symbol="BR_CONT",
            candidates=["BRM6@RTSX", "BRN6@RTSX"],
        )

    def choose(
        self,
        continuous_symbol: str,
        candidates: list[str],
    ) -> ContractLiquidityDecision | None:
        sql = """
        with latest_sm as (
            select distinct on (symbol)
                symbol,
                smart_money_score,
                rvol
            from smart_money_feature_events
            where symbol = any(%s)
            order by symbol, ts desc
        ),
        latest_metrics as (
            select distinct on (symbol)
                symbol,
                turnover,
                spread_pct
            from market_opportunity_metrics
            where symbol = any(%s)
            order by symbol, calculated_at desc
        )
        select
            c.symbol,
            coalesce(sm.smart_money_score, 0) as smart_money_score,
            coalesce(sm.rvol, 0) as rvol,
            coalesce(m.turnover, 0) as turnover,
            coalesce(m.spread_pct, 0) as spread_pct
        from unnest(%s::text[]) as c(symbol)
        left join latest_sm sm on sm.symbol = c.symbol
        left join latest_metrics m on m.symbol = c.symbol
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (candidates, candidates, candidates))
                rows = cur.fetchall()

        if not rows:
            return None

        best_symbol = ""
        best_score = -1.0
        reasons: list[str] = []

        for symbol, smart_money_score, rvol, turnover, spread_pct in rows:
            smart_money_score = float(smart_money_score or 0.0)
            rvol = float(rvol or 0.0)
            turnover = float(turnover or 0.0)
            spread_pct = float(spread_pct or 0.0)

            turnover_score = min(turnover / 1_000_000_000.0, 1.0)
            rvol_score = min(rvol / 3.0, 1.0)
            spread_penalty = min(spread_pct / 0.01, 1.0)

            score = round(
                smart_money_score * 0.40
                + rvol_score * 0.30
                + turnover_score * 0.20
                - spread_penalty * 0.10,
                6,
            )

            reasons.append(
                f"{symbol}:score={score};smart_money={smart_money_score};"
                f"rvol={rvol};turnover={turnover};spread={spread_pct}"
            )

            if score > best_score:
                best_score = score
                best_symbol = str(symbol)

        return ContractLiquidityDecision(
            continuous_symbol=continuous_symbol,
            preferred_symbol=best_symbol,
            score=best_score,
            reason=" | ".join(reasons),
            candidates=[str(x) for x in candidates],
        )
