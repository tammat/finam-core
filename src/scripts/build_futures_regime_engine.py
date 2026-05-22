from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.futures_regime_engine import FuturesRegimeEngine


def load_contracts(roots: list[str], max_contracts: int) -> list[str]:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT contract_symbol
                FROM futures_contract_universe
                WHERE root_symbol = ANY(%s)
                  AND is_active = TRUE
                  AND status <> 'QUARANTINE'
                ORDER BY root_symbol, roll_priority, expiration_date NULLS LAST
                """,
                (roots,),
            )
            rows = cur.fetchall()

    result: list[str] = []
    per_root: dict[str, int] = {}

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for (contract,) in rows:
                cur.execute(
                    """
                    SELECT root_symbol
                    FROM futures_contract_universe
                    WHERE contract_symbol=%s
                    """,
                    (contract,),
                )
                root = cur.fetchone()[0]
                per_root[root] = per_root.get(root, 0) + 1
                if per_root[root] <= max_contracts:
                    result.append(contract)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", default="BR,NG,USD")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--max-contracts", type=int, default=3)
    args = parser.parse_args()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]

    contracts = load_contracts(roots, args.max_contracts)
    engine = FuturesRegimeEngine()

    saved = 0

    for contract in contracts:
        state = engine.calculate_and_save(
            symbol=contract,
            timeframe=args.timeframe,
        )
        saved += 1

        print(
            "FUTURES_REGIME_ENGINE "
            f"symbol={state.symbol} "
            f"timeframe={state.timeframe} "
            f"regime={state.regime} "
            f"trend={state.trend} "
            f"volatility={state.volatility} "
            f"atr={round(state.atr, 6)} "
            f"bars={state.bars} "
            f"reason={state.reason}",
            flush=True,
        )

    print(
        "FUTURES_REGIME_ENGINE_SUMMARY "
        f"contracts={len(contracts)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
