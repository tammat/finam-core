from __future__ import annotations

from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class PortfolioRiskDecision:
    allowed: bool
    cluster_name: str
    risk_state: str
    reason: str


class PortfolioRiskGate:

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def classify_cluster(self, symbol: str) -> str:
        s = symbol.upper()

        if s.startswith("NG") or s.startswith("BR"):
            return "COMMODITIES"

        if "USD" in s or "RUB" in s:
            return "FX"

        return "EQUITIES"

    def check(self, symbol: str) -> PortfolioRiskDecision:

        cluster = self.classify_cluster(symbol)

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT risk_state, portfolio_share, reason
                    FROM portfolio_risk_state
                    WHERE cluster_name=%s
                    LIMIT 1
                """, (cluster,))
                row = cur.fetchone()

        if not row:
            return PortfolioRiskDecision(
                allowed=True,
                cluster_name=cluster,
                risk_state="UNKNOWN",
                reason="portfolio_risk_state_missing_soft_allow",
            )

        risk_state, portfolio_share, reason = row

        if risk_state == "OVEREXPOSED":
            return PortfolioRiskDecision(
                allowed=False,
                cluster_name=cluster,
                risk_state=risk_state,
                reason=f"portfolio_cluster_overexposed share={portfolio_share} reason={reason}",
            )

        return PortfolioRiskDecision(
            allowed=True,
            cluster_name=cluster,
            risk_state=risk_state,
            reason=f"portfolio_risk_ok share={portfolio_share} reason={reason}",
        )
