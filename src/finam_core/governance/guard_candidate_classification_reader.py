from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import os
import psycopg2
import psycopg2.extras


ClassificationKey = Tuple[str, str, str, str, str]


@dataclass(frozen=True, slots=True)
class GuardCandidateClassification:
    symbol: str
    strategy: str
    timeframe: str
    side: str
    session_bucket: str
    classification: str
    reason: str
    total_trades: int
    total_net_pnl: float
    expectancy: float
    stop_rate: float
    take_rate: float
    pf_proxy: Optional[float]


class GuardCandidateClassificationReader:
    def __init__(self, dsn: Optional[str] = None, source: str = "guard_candidate_classification_v1"):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        self.source = source
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def load_all(self) -> Dict[ClassificationKey, GuardCandidateClassification]:
        sql = """
            select
                symbol,
                strategy,
                timeframe,
                side,
                session_bucket,
                classification,
                reason,
                total_trades,
                total_net_pnl,
                expectancy,
                stop_rate,
                take_rate,
                pf_proxy
            from guard_candidate_classification_state
            where source = %s
            order by symbol, strategy, timeframe, side, session_bucket
        """

        result: Dict[ClassificationKey, GuardCandidateClassification] = {}

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, (self.source,))
                rows = cur.fetchall()

        for row in rows:
            item = GuardCandidateClassification(
                symbol=str(row["symbol"]),
                strategy=str(row["strategy"]),
                timeframe=str(row["timeframe"]),
                side=str(row["side"]),
                session_bucket=str(row["session_bucket"]),
                classification=str(row["classification"]),
                reason=str(row["reason"]),
                total_trades=int(row["total_trades"] or 0),
                total_net_pnl=float(row["total_net_pnl"] or 0),
                expectancy=float(row["expectancy"] or 0),
                stop_rate=float(row["stop_rate"] or 0),
                take_rate=float(row["take_rate"] or 0),
                pf_proxy=None if row["pf_proxy"] is None else float(row["pf_proxy"]),
            )

            key = (
                item.symbol,
                item.strategy,
                item.timeframe,
                item.side,
                item.session_bucket,
            )
            result[key] = item

        return result

    def get(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        side: str,
        session_bucket: str,
    ) -> Optional[GuardCandidateClassification]:
        data = self.load_all()
        return data.get((
            str(symbol),
            str(strategy),
            str(timeframe),
            str(side).upper(),
            str(session_bucket),
        ))
