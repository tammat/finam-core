from __future__ import annotations

from finam_core.common.strategy_names import normalize_strategy_name

import argparse

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.strategy_promotion_feed_repository import StrategyPromotionFeedRepository

# TRUSTED_RUNTIME_GATE_V1_WIRE:
# Русский комментарий:
# Trusted Runtime Gate является последним fail-closed фильтром перед promotion feed.
# Если связка отсутствует в trusted candidates или явно заблокирована,
# она не может получить paper/radar/real допуск независимо от walkforward.
def _load_trusted_runtime_gate(conn):
    sql = """
    select
        symbol,
        strategy,
        timeframe,
        trade_source,
        gate_status,
        gate_reason,
        allow_promotion,
        allow_paper_runtime,
        allow_real_runtime
    from trusted_runtime_gate_v1
    """
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
    except Exception:
        # Fail-closed: если таблицы gate нет или она недоступна,
        # считаем, что нет ни одной разрешённой стратегии.
        return {}

    result = {}
    for row in rows:
        result[(row[0], row[1], row[2], row[3])] = {
            "gate_status": row[4],
            "gate_reason": row[5],
            "allow_promotion": bool(row[6]),
            "allow_paper_runtime": bool(row[7]),
            "allow_real_runtime": bool(row[8]),
        }
    return result


def _apply_trusted_runtime_gate(decision, gate_map):
    key = (
        decision.symbol,
        decision.strategy,
        decision.timeframe,
        decision.trade_source,
    )
    gate = gate_map.get(key)

    if not gate:
        return type(decision)(
            symbol=decision.symbol,
            strategy=decision.strategy,
            timeframe=decision.timeframe,
            trade_source=decision.trade_source,
            runtime_action="BLOCK",
            allow_paper_signal=False,
            allow_radar_signal=False,
            allow_real_suggestion=False,
            reason="trusted_runtime_gate_missing_or_closed",
        )

    if gate["gate_status"] != "OPEN" or not gate["allow_promotion"]:
        return type(decision)(
            symbol=decision.symbol,
            strategy=decision.strategy,
            timeframe=decision.timeframe,
            trade_source=decision.trade_source,
            runtime_action="BLOCK",
            allow_paper_signal=False,
            allow_radar_signal=False,
            allow_real_suggestion=False,
            reason=f"trusted_runtime_gate_block:{gate['gate_reason']}",
        )

    return type(decision)(
        symbol=decision.symbol,
        strategy=decision.strategy,
        timeframe=decision.timeframe,
        trade_source=decision.trade_source,
        runtime_action=decision.runtime_action,
        allow_paper_signal=decision.allow_paper_signal and gate["allow_paper_runtime"],
        allow_radar_signal=decision.allow_radar_signal,
        allow_real_suggestion=decision.allow_real_suggestion and gate["allow_real_runtime"],
        reason=f"{decision.reason}|trusted_runtime_gate_open",
    )

from finam_core.runtime.strategy_promotion_feed import (
    StrategyPromotionInput,
    build_strategy_promotion_decision,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    where = ""
    params = []

    if args.symbol:
        where = "WHERE symbol = %s"
        params.append(args.symbol)

    sql = f"""
    SELECT symbol, strategy, timeframe, trade_source,
           score, rank_status, reason
    FROM strategy_ranking_v2
    {where}
    ORDER BY score DESC, calculated_at DESC
    LIMIT %s
    """
    params.append(args.limit)

    decisions = []

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            for row in cur.fetchall():
                decisions.append(
                    build_strategy_promotion_decision(
                        StrategyPromotionInput(
                            symbol=str(row[0]),
                            strategy=normalize_strategy_name(str(row[1])),
                            timeframe=str(row[2]),
                            trade_source=str(row[3]),
                            score=float(row[4] or 0.0),
                            rank_status=str(row[5]),
                            reason=str(row[6]),
                        )
                    )
                )

    saved = 0
    if args.migrate or args.save:
        feed_repo = StrategyPromotionFeedRepository(build_psycopg_url())
        feed_repo.migrate()

    if args.save:
        
        # TRUSTED_RUNTIME_GATE_V1_WIRE:
        # Русский комментарий:
        # Перед сохранением promotion feed принудительно применяем trusted gate.
        # Это защищает runtime от старой/загрязнённой статистики.
        with psycopg.connect(build_psycopg_url()) as gate_conn:
            gate_map = _load_trusted_runtime_gate(gate_conn)

        decisions = [
            _apply_trusted_runtime_gate(item, gate_map)
            for item in decisions
        ]

        
        saved = feed_repo.save(decisions)

        # TRUSTED_RUNTIME_GATE_V1_POST_SAVE_ENFORCE:
        # Русский комментарий:
        # Repository может оставить старые строки promotion feed.
        # Поэтому после сохранения принудительно закрываем все строки,
        # которых нет в trusted_runtime_gate_v1 со статусом OPEN.
        with psycopg.connect(build_psycopg_url()) as enforce_conn:
            with enforce_conn.cursor() as cur:
                cur.execute("""
                    update strategy_promotion_runtime_feed f
                    set
                        runtime_action='BLOCK',
                        allow_paper_signal=false,
                        allow_radar_signal=false,
                        allow_real_suggestion=false,
                        reason=case
                            when g.gate_status is null
                                then 'trusted_runtime_gate_missing_or_closed'
                            else 'trusted_runtime_gate_block:' || g.gate_reason
                        end,
                        updated_at=now()
                    from trusted_runtime_gate_v1 g
                    where f.symbol=g.symbol
                      and f.strategy=g.strategy
                      and f.timeframe=g.timeframe
                      and f.trade_source=g.trade_source
                      and (
                          g.gate_status <> 'OPEN'
                          or coalesce(g.allow_promotion,false)=false
                      );
                """)
                cur.execute("""
                    update strategy_promotion_runtime_feed f
                    set
                        runtime_action='BLOCK',
                        allow_paper_signal=false,
                        allow_radar_signal=false,
                        allow_real_suggestion=false,
                        reason='trusted_runtime_gate_missing_or_closed',
                        updated_at=now()
                    where not exists (
                        select 1
                        from trusted_runtime_gate_v1 g
                        where g.symbol=f.symbol
                          and g.strategy=f.strategy
                          and g.timeframe=f.timeframe
                          and g.trade_source=f.trade_source
                          and g.gate_status='OPEN'
                          and coalesce(g.allow_promotion,false)=true
                    );
                """)
            enforce_conn.commit()


    for item in decisions:
        print(
            "STRATEGY_PROMOTION_FEED "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"source={item.trade_source} "
            f"action={item.runtime_action} "
            f"paper={item.allow_paper_signal} "
            f"radar={item.allow_radar_signal} "
            f"real_suggestion={item.allow_real_suggestion} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "STRATEGY_PROMOTION_FEED_SUMMARY "
        f"total={len(decisions)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
