# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.infra.finam.client import FinamClient
from finam_core.storage.real_position_snapshot_repository import RealPositionSnapshotRepository


def normalize_position(p: dict) -> dict:
    return {
        "symbol": p.get("symbol") or p.get("security_code") or p.get("ticker") or "",
        "qty": p.get("qty") or p.get("balance") or p.get("quantity") or 0.0,
        "avg_price": p.get("avg_price") or p.get("average_price"),
        "market_price": p.get("market_price") or p.get("price") or p.get("last_price"),
        "unrealized_pnl": p.get("unrealized_pnl") or p.get("pnl"),
        "raw": p,
    }


def main() -> int:
    client = FinamClient()
    raw_positions = client.get_positions()

    positions = [normalize_position(p) for p in raw_positions]
    saved = RealPositionSnapshotRepository().save_positions(positions)

    print(f"REAL_POSITION_SYNC_OK positions={len(positions)} saved={saved}")

    for p in positions:
        print(
            f"REAL_POSITION symbol={p['symbol']} qty={p['qty']} "
            f"avg={p['avg_price']} price={p['market_price']} pnl={p['unrealized_pnl']}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
