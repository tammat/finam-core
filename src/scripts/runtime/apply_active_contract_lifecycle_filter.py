from __future__ import annotations

import os

import psycopg

from finam_core.research.active_contract_lifecycle_filter import (
    is_active_contract_edge_confirmed,
)


def _active_symbol_for_root(root_symbol: str) -> str:
    """Русский комментарий: активный контракт задаём через env, чтобы не хардкодить календарь экспирации."""
    if root_symbol == "NG":
        return os.getenv("ACTIVE_NG_SYMBOL", "NGM6@RTSX")
    if root_symbol == "BR":
        return os.getenv("ACTIVE_BR_SYMBOL", "BRM6@RTSX")
    if root_symbol == "USDRUB":
        return os.getenv("ACTIVE_USDRUB_SYMBOL", "USDRUBF@RTSX")
    return root_symbol


def main() -> None:
    """
    Русский комментарий:
    Защитный фильтр promotion-слоя.

    Если strategy_selection_state содержит PROMOTED_RUNTIME,
    но активный контракт не подтвердил edge в closed_trade_quality_stats,
    статус откатывается в ENABLED_RESEARCH.
    """
    database_url = os.environ["DATABASE_URL"]
    default_timeframe = os.getenv("ACTIVE_CONTRACT_TIMEFRAME", "M5")

    promoted_sql = """
    SELECT
        strategy,
        symbol,
        root_symbol,
        regime,
        status
    FROM strategy_selection_state
    WHERE status = 'PROMOTED_RUNTIME';
    """

    stats_sql = """
    SELECT
        trades,
        avg_net_pnl,
        win_rate
    FROM closed_trade_quality_stats
    WHERE root_symbol = %(root_symbol)s
      AND symbol = %(active_symbol)s
      AND strategy = %(strategy)s
      AND timeframe = %(timeframe)s
    LIMIT 1;
    """

    downgrade_sql = """
    UPDATE strategy_selection_state
    SET
        status = 'ENABLED_RESEARCH',
        updated_at = now(),
        reason = reason || %(reason_suffix)s
    WHERE strategy = %(strategy)s
      AND root_symbol = %(root_symbol)s
      AND regime = %(regime)s
      AND status = 'PROMOTED_RUNTIME';
    """

    checked = 0
    downgraded = 0
    kept = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(promoted_sql)
            promoted_rows = cur.fetchall()

            for strategy, symbol, root_symbol, regime, status in promoted_rows:
                checked += 1
                root_symbol = str(root_symbol)
                strategy = str(strategy)
                regime = str(regime)
                active_symbol = _active_symbol_for_root(root_symbol)

                cur.execute(
                    stats_sql,
                    {
                        "root_symbol": root_symbol,
                        "active_symbol": active_symbol,
                        "strategy": strategy,
                        "timeframe": default_timeframe,
                    },
                )
                stats = cur.fetchone()

                if stats is None:
                    decision = is_active_contract_edge_confirmed(
                        root_symbol=root_symbol,
                        active_symbol=active_symbol,
                        strategy=strategy,
                        timeframe=default_timeframe,
                        trades=0,
                        avg_net_pnl=0.0,
                        win_rate=0.0,
                    )
                else:
                    trades, avg_net_pnl, win_rate = stats
                    decision = is_active_contract_edge_confirmed(
                        root_symbol=root_symbol,
                        active_symbol=active_symbol,
                        strategy=strategy,
                        timeframe=default_timeframe,
                        trades=int(trades),
                        avg_net_pnl=float(avg_net_pnl),
                        win_rate=float(win_rate),
                    )

                if not decision.allowed:
                    cur.execute(
                        downgrade_sql,
                        {
                            "strategy": strategy,
                            "root_symbol": root_symbol,
                            "regime": regime,
                            "reason_suffix": (
                                " | lifecycle_filter_downgraded:"
                                f"{decision.reason}"
                                f":active={active_symbol}"
                                f":trades={decision.trades}"
                                f":avg_net_pnl={decision.avg_net_pnl}"
                                f":win_rate={decision.win_rate}"
                            ),
                        },
                    )
                    downgraded += 1
                    print(
                        "ACTIVE_CONTRACT_PROMOTION_DOWNGRADED "
                        f"strategy={strategy} root_symbol={root_symbol} "
                        f"active_symbol={active_symbol} regime={regime} "
                        f"reason={decision.reason} trades={decision.trades} "
                        f"avg_net_pnl={decision.avg_net_pnl} win_rate={decision.win_rate}",
                        flush=True,
                    )
                else:
                    kept += 1
                    print(
                        "ACTIVE_CONTRACT_PROMOTION_KEPT "
                        f"strategy={strategy} root_symbol={root_symbol} "
                        f"active_symbol={active_symbol} regime={regime} "
                        f"trades={decision.trades} avg_net_pnl={decision.avg_net_pnl} "
                        f"win_rate={decision.win_rate}",
                        flush=True,
                    )

        conn.commit()

    print(
        "ACTIVE_CONTRACT_LIFECYCLE_FILTER_DONE "
        f"checked={checked} kept={kept} downgraded={downgraded}",
        flush=True,
    )


if __name__ == "__main__":
    main()
