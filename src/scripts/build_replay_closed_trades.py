from __future__ import annotations

import argparse

from finam_core.analytics.closed_trade_engine import ClosedTradeEngine, TradeFill
from finam_core.analytics.closed_trade_repository import ClosedTradeRepository
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-id", required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    select id, ts, symbol, side, qty, price, commission, fill_id, payload
    from trades
    where payload->>'replay_campaign_id' = %s
    order by ts, id
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_id,))
            rows = cur.fetchall()

        fills = [
            TradeFill(
                id=int(r[0]),
                ts=str(r[1]),
                symbol=str(r[2]),
                side=str(r[3]),
                qty=float(r[4]),
                price=float(r[5]),
                commission=float(r[6] or 0.0),
                fill_id=r[7],
                payload=r[8] or {},
            )
            for r in rows
        ]

        closed = ClosedTradeEngine().build_closed_trades(fills)
        saved = ClosedTradeRepository(conn).save_closed_trades(closed, trade_source="paper")

    print(
        f"REPLAY_CLOSED_TRADES_OK campaign_id={args.campaign_id} fills={len(fills)} closed={len(closed)} saved={saved}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
