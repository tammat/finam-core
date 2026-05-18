from __future__ import annotations

import argparse

from finam_core.analytics.statistical_validation_engine import StatisticalValidationEngine
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pg = PostgresLogger()

    sql = """
    select net_pnl
    from closed_trades
    where coalesce(
        payload->>'replay_campaign_id',
        payload->'payload'->>'replay_campaign_id'
    ) = %s
      and trade_source = 'paper'
    order by exit_ts, id
    """

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.campaign_id,))
            pnl_values = [float(row[0]) for row in cur.fetchall()]

    result = StatisticalValidationEngine().validate(
        pnl_values,
        bootstrap_samples=args.bootstrap_samples,
    )

    print(
        "CAMPAIGN_STAT_VALIDATION "
        f"campaign_id={args.campaign_id} "
        f"trades={result.trades} "
        f"net_pnl={result.net_pnl:.6f} "
        f"expectancy={result.expectancy:.6f} "
        f"winrate={result.winrate:.4f} "
        f"bootstrap_expectancy={result.bootstrap_mean_expectancy:.6f} "
        f"ci_low={result.expectancy_ci_low:.6f} "
        f"ci_high={result.expectancy_ci_high:.6f} "
        f"p_positive={result.probability_positive_expectancy:.4f}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
