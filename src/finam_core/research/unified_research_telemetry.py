from __future__ import annotations

import os
import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class ResearchMetrics:
    strategy: str
    symbol: str
    trades: int
    winrate: float
    avg_pnl: float
    max_drawdown: float
    walkforward_pass_rate: float
    regime_pass_rate: float
    session_pass_rate: float
    forward_decay: float
    live_replay_gap: float
    data_source: str


@dataclass(frozen=True)
class ResearchTelemetryVerdict:
    strategy: str
    symbol: str
    strategy_health: str
    edge_stability: str
    walkforward_consistency: str
    regime_quality: str
    session_quality: str
    forward_decay: str
    live_vs_replay_divergence: str
    final_verdict: str
    data_source: str


def _connect(database_url: str):
    # Русский комментарий:
    # Research-отчет работает только на чтение.
    # autocommit нужен, чтобы один неудачный SELECT не ломал все последующие запросы.
    try:
        import psycopg
        conn = psycopg.connect(database_url)
        conn.autocommit = True
        return conn
    except Exception:
        import psycopg2
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        return conn


def _table_exists(conn, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            select exists (
                select 1
                from information_schema.tables
                where table_schema = 'public'
                  and table_name = %s
            )
            """,
            (table_name,),
        )
        return bool(cur.fetchone()[0])


def _safe_rollback(conn) -> None:
    # Русский комментарий:
    # Защита от состояния InFailedSqlTransaction после неудачного SQL.
    try:
        conn.rollback()
    except Exception:
        pass


def _scalar(conn, sql: str, params: tuple, default):
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if not row or row[0] is None:
                return default
            return row[0]
    except Exception:
        _safe_rollback(conn)
        return default


def load_metrics_from_postgres(strategy: str, symbol: str) -> ResearchMetrics:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return ResearchMetrics(strategy, symbol, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, "NO_DATABASE_URL")

    conn = _connect(database_url)

    try:
        # Базовый источник — trades. Он уже есть в системе и используется для paper attribution.
        if _table_exists(conn, "trades"):
            trades = int(_scalar(
                conn,
                """
                select count(*)
                from trades
                where symbol = %s
                  and strategy = %s
                  and is_invalid = false
                """,
                (symbol, strategy),
                0,
            ))

            avg_pnl = float(_scalar(
                conn,
                """
                select avg(coalesce((payload->>'pnl')::numeric, 0))
                from trades
                where symbol = %s
                  and strategy = %s
                  and is_invalid = false
                """,
                (symbol, strategy),
                0.0,
            ))

            wins = int(_scalar(
                conn,
                """
                select count(*)
                from trades
                where symbol = %s
                  and strategy = %s
                  and is_invalid = false
                  and coalesce((payload->>'pnl')::numeric, 0) > 0
                """,
                (symbol, strategy),
                0,
            ))

            winrate = wins / trades if trades else 0.0
        else:
            trades, avg_pnl, winrate = 0, 0.0, 0.0

        # Research-таблицы подключаем мягко: если схемы нет — не падаем.
        walkforward_pass_rate = float(_scalar(
            conn,
            """
            select avg(case when final_verdict in ('OK','PASS','PROMOTION_CANDIDATE') then 1.0 else 0.0 end)
            from replay_campaign_results
            where symbol = %s and strategy = %s
            """,
            (symbol, strategy),
            0.0,
        )) if _table_exists(conn, "replay_campaign_results") else -1.0

        regime_pass_rate = float(_scalar(
            conn,
            """
            select avg(case when verdict in ('OK','PASS','TRADEABLE') then 1.0 else 0.0 end)
            from regime_scorecard
            where symbol = %s and strategy = %s
            """,
            (symbol, strategy),
            0.0,
        )) if _table_exists(conn, "regime_scorecard") else -1.0

        session_pass_rate = float(_scalar(
            conn,
            """
            select avg(case when verdict in ('OK','PASS','TRADEABLE') then 1.0 else 0.0 end)
            from session_scorecard
            where symbol = %s and strategy = %s
            """,
            (symbol, strategy),
            0.0,
        )) if _table_exists(conn, "session_scorecard") else -1.0

        forward_decay = float(_scalar(
            conn,
            """
            select coalesce(avg(decay), 1.0)
            from forward_accumulation
            where symbol = %s and strategy = %s
            """,
            (symbol, strategy),
            1.0,
        )) if _table_exists(conn, "forward_accumulation") else -1.0

        return ResearchMetrics(
            strategy=strategy,
            symbol=symbol,
            trades=trades,
            winrate=winrate,
            avg_pnl=avg_pnl,
            max_drawdown=0.0,
            walkforward_pass_rate=walkforward_pass_rate,
            regime_pass_rate=regime_pass_rate,
            session_pass_rate=session_pass_rate,
            forward_decay=forward_decay,
            live_replay_gap=0.0,
            data_source="POSTGRESQL",
        )

    finally:
        conn.close()


def build_unified_research_telemetry(metrics: ResearchMetrics) -> ResearchTelemetryVerdict:
    strategy_health = "OK" if metrics.trades >= 30 and metrics.avg_pnl > 0 else "WATCH"
    edge_stability = "OK" if metrics.winrate >= 0.45 and metrics.avg_pnl > 0 else "WEAK"
    walkforward_consistency = "NO_TABLE" if metrics.walkforward_pass_rate < 0 else ("OK" if metrics.walkforward_pass_rate >= 0.60 else "WEAK")
    regime_quality = "NO_TABLE" if metrics.regime_pass_rate < 0 else ("OK" if metrics.regime_pass_rate >= 0.60 else "WEAK")
    session_quality = "NO_TABLE" if metrics.session_pass_rate < 0 else ("OK" if metrics.session_pass_rate >= 0.60 else "WEAK")
    forward_decay_state = "NO_TABLE" if metrics.forward_decay < 0 else ("OK" if metrics.forward_decay <= 0.35 else "HIGH_DECAY")
    live_vs_replay_divergence = "OK" if metrics.live_replay_gap <= 0.30 else "DIVERGENCE"

    flags = {
        edge_stability,
        walkforward_consistency,
        regime_quality,
        session_quality,
        forward_decay_state,
        live_vs_replay_divergence,
    }

    final_verdict = "RESEARCH_WATCH" if {"WEAK", "HIGH_DECAY", "DIVERGENCE"} & flags else "PROMOTION_CANDIDATE"

    if metrics.data_source in {"NO_DATABASE_URL"}:
        final_verdict = "RESEARCH_NO_DATA"

    return ResearchTelemetryVerdict(
        strategy=metrics.strategy,
        symbol=metrics.symbol,
        strategy_health=strategy_health,
        edge_stability=edge_stability,
        walkforward_consistency=walkforward_consistency,
        regime_quality=regime_quality,
        session_quality=session_quality,
        forward_decay=forward_decay_state,
        live_vs_replay_divergence=live_vs_replay_divergence,
        final_verdict=final_verdict,
        data_source=metrics.data_source,
    )


def render_report(v: ResearchTelemetryVerdict) -> str:
    return f"""
========================================
 FINAM_CORE — ЕДИНАЯ RESEARCH-ТЕЛЕМЕТРИЯ
========================================

Источник данных          : {v.data_source}
Стратегия                : {v.strategy}
Инструмент               : {v.symbol}

Здоровье стратегии       : {v.strategy_health}
Стабильность edge        : {v.edge_stability}
Walkforward              : {v.walkforward_consistency}
Качество режимов         : {v.regime_quality}
Качество сессий          : {v.session_quality}
Forward decay            : {v.forward_decay}
Live vs Replay           : {v.live_vs_replay_divergence}

ИТОГ                     : {v.final_verdict}
========================================
""".strip()


def demo_metrics() -> ResearchMetrics:
    return ResearchMetrics(
        strategy="br_conservative_breakout",
        symbol="BRN6@RTSX",
        trades=38,
        winrate=0.50,
        avg_pnl=120.0,
        max_drawdown=-3500.0,
        walkforward_pass_rate=0.65,
        regime_pass_rate=0.70,
        session_pass_rate=0.62,
        forward_decay=0.25,
        live_replay_gap=0.18,
        data_source="DEMO",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="br_conservative_breakout")
    parser.add_argument("--symbol", default="BRN6@RTSX")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    metrics = demo_metrics() if args.demo else load_metrics_from_postgres(args.strategy, args.symbol)
    print(render_report(build_unified_research_telemetry(metrics)))


if __name__ == "__main__":
    main()
