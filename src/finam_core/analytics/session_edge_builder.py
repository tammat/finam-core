from dataclasses import dataclass
from typing import Dict, Iterable, List

from finam_core.analytics.edge_validation import EdgeBucket, build_edge_bucket
from finam_core.analytics.trade_pnl_reconstructor import reconstruct_closed_trades
from finam_core.analytics.trade_session_segmenter import TradeSession, build_trade_sessions


@dataclass(frozen=True)
class SessionEdgeResult:
    session: TradeSession
    bucket: EdgeBucket


def build_session_edge_results(rows: Iterable[dict]) -> List[SessionEdgeResult]:
    # Pipeline:
    # trades -> sessions -> FIFO внутри session -> clean PnL -> edge bucket.
    ordered = list(rows)
    sessions = build_trade_sessions(ordered)

    result: List[SessionEdgeResult] = []

    for session in sessions:
        session_rows = [
            row
            for row in ordered
            if session.start_trade_id <= int(row["id"]) <= session.end_trade_id
        ]

        closed = reconstruct_closed_trades(session_rows)
        pnl_values = [x.net_pnl for x in closed]

        profile = (
            f"source={session.trade_source}|"
            f"strategy={session.strategy or 'NA'}|"
            f"timeframe={session.timeframe or 'NA'}|"
            f"session={session.session_id}"
        )

        symbol = str(session_rows[0].get("symbol") or "") if session_rows else ""

        bucket = build_edge_bucket(
            symbol=symbol,
            profile=profile,
            pnl_values=pnl_values,
        )

        result.append(
            SessionEdgeResult(
                session=session,
                bucket=bucket,
            )
        )

    return result


def aggregate_edge_by_profile(results: Iterable[SessionEdgeResult]) -> Dict[str, EdgeBucket]:
    grouped: Dict[str, List[float]] = {}
    symbols: Dict[str, str] = {}

    for item in results:
        profile = (
            f"source={item.session.trade_source}|"
            f"strategy={item.session.strategy or 'NA'}|"
            f"timeframe={item.session.timeframe or 'NA'}"
        )

        grouped.setdefault(profile, [])
        symbols[profile] = item.bucket.symbol

        # В bucket нет исходного списка PnL, поэтому на этом этапе агрегируем
        # через средний PnL * trades. Для точной агрегации ниже используем runner,
        # где PnL считается напрямую по closed trades.
        if item.bucket.trades:
            grouped[profile].extend([item.bucket.avg_pnl] * item.bucket.trades)

    return {
        profile: build_edge_bucket(
            symbol=symbols.get(profile, ""),
            profile=profile,
            pnl_values=values,
        )
        for profile, values in grouped.items()
    }
