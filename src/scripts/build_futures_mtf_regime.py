from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.futures_mtf_regime_aggregator import (
    FuturesMtfRegimeAggregator,
)


def load_symbols(roots: list[str], max_contracts: int) -> list[str]:
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
            rows = [r[0] for r in cur.fetchall()]

    result: list[str] = []
    per_root: dict[str, int] = {}

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for symbol in rows:
                cur.execute(
                    "SELECT root_symbol FROM futures_contract_universe WHERE contract_symbol=%s",
                    (symbol,),
                )
                root = cur.fetchone()[0]
                per_root[root] = per_root.get(root, 0) + 1
                if per_root[root] <= max_contracts:
                    result.append(symbol)

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", default="BR,NG,USD")
    parser.add_argument("--max-contracts", type=int, default=3)
    parser.add_argument("--macro-tf", default="H1")
    parser.add_argument("--structure-tf", default="M15")
    parser.add_argument("--execution-tf", default="M5")
    args = parser.parse_args()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]

    agg = FuturesMtfRegimeAggregator()
    agg.migrate()

    symbols = load_symbols(roots, args.max_contracts)

    saved = 0

    for symbol in symbols:
        item = agg.calculate_symbol(
            symbol=symbol,
            macro_tf=args.macro_tf,
            structure_tf=args.structure_tf,
            execution_tf=args.execution_tf,
        )
        agg.save(item, structure_tf=args.structure_tf)
        saved += 1

        print(
            "FUTURES_MTF_REGIME "
            f"symbol={item.symbol} "
            f"root={item.root_symbol} "
            f"macro={item.macro_regime}/{item.macro_trend} "
            f"execution={item.execution_regime}/{item.execution_trend} "
            f"volatility={item.volatility_state} "
            f"alignment={item.bias_alignment} "
            f"tradable={item.tradable} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "FUTURES_MTF_REGIME_SUMMARY "
        f"symbols={len(symbols)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
