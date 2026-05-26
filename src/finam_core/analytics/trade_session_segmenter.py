from dataclasses import dataclass
from datetime import timedelta
from typing import Iterable, List


MAX_TS_GAP = timedelta(minutes=30)


@dataclass(frozen=True)
class TradeSession:
    session_id: int
    start_trade_id: int
    end_trade_id: int
    fills: int
    strategy: str
    timeframe: str
    trade_source: str


def build_trade_sessions(rows: Iterable[dict]) -> List[TradeSession]:
    # Делим журнал trades на независимые execution sessions.
    # Это защищает PnL от ошибочного FIFO-склеивания разных прогонов.
    ordered = list(rows)

    if not ordered:
        return []

    sessions: List[TradeSession] = []

    current_session_id = 1
    start = ordered[0]
    prev = ordered[0]
    fills = 1

    for row in ordered[1:]:
        new_session = False

        id_gap = int(row["id"]) - int(prev["id"])
        ts_gap = row["ts"] - prev["ts"]

        if id_gap <= 0:
            new_session = True

        if ts_gap > MAX_TS_GAP:
            new_session = True

        if row.get("strategy") != prev.get("strategy"):
            new_session = True

        if row.get("timeframe") != prev.get("timeframe"):
            new_session = True

        if row.get("trade_source") != prev.get("trade_source"):
            new_session = True

        if new_session:
            sessions.append(
                TradeSession(
                    session_id=current_session_id,
                    start_trade_id=int(start["id"]),
                    end_trade_id=int(prev["id"]),
                    fills=fills,
                    strategy=str(start.get("strategy") or ""),
                    timeframe=str(start.get("timeframe") or ""),
                    trade_source=str(start.get("trade_source") or ""),
                )
            )

            current_session_id += 1
            start = row
            fills = 1
        else:
            fills += 1

        prev = row

    sessions.append(
        TradeSession(
            session_id=current_session_id,
            start_trade_id=int(start["id"]),
            end_trade_id=int(prev["id"]),
            fills=fills,
            strategy=str(start.get("strategy") or ""),
            timeframe=str(start.get("timeframe") or ""),
            trade_source=str(start.get("trade_source") or ""),
        )
    )

    return sessions
