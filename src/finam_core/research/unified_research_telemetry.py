from __future__ import annotations

import os
import argparse
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UnifiedResearchSnapshot:
    symbol: str
    strategy: str
    timeframe: str

    production_status: str
    projection_lag: int
    dlq_unresolved: int

    research_supervisor_status: str
    research_last_error: str

    trades: int
    profit_factor: float
    winrate: float
    expectancy: float
    strategy_status: str

    promotion_decision: str
    lifecycle_state: str
    allow_runtime: bool
    allow_research: bool
    reason: str

    final_verdict: str


def _connect(database_url: str):
    # Русский комментарий:
    # Отчет только читает PostgreSQL. autocommit защищает от зависших транзакций после ошибочного SELECT.
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


def _safe_row(conn, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    # Русский комментарий:
    # Универсальный безопасный SELECT одной строки. При ошибке возвращает пустой словарь.
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if row is None:
                return {}
            columns = [d[0] for d in cur.description]
            return dict(zip(columns, row))
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_bool(value: Any) -> bool:
    return bool(value)


def load_snapshot_from_postgres(symbol: str, strategy: str, timeframe: str) -> UnifiedResearchSnapshot:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return UnifiedResearchSnapshot(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            production_status="NO_DATABASE_URL",
            projection_lag=-1,
            dlq_unresolved=-1,
            research_supervisor_status="NO_DATABASE_URL",
            research_last_error="NO_DATABASE_URL",
            trades=0,
            profit_factor=0.0,
            winrate=0.0,
            expectancy=0.0,
            strategy_status="NO_DATA",
            promotion_decision="NO_DATA",
            lifecycle_state="NO_DATA",
            allow_runtime=False,
            allow_research=False,
            reason="DATABASE_URL не задан",
            final_verdict="RESEARCH_NO_DATA",
        )

    conn = _connect(database_url)
    try:
        health = _safe_row(
            conn,
            """
            select projection_lag, dlq_unresolved
            from v_production_health
            limit 1
            """,
        )

        projection_lag = _to_int(health.get("projection_lag"), -1)
        dlq_unresolved = _to_int(health.get("dlq_unresolved"), -1)

        production_status = (
            "OK"
            if projection_lag == 0 and dlq_unresolved == 0
            else "DEGRADED"
        )

        research = _safe_row(
            conn,
            """
            select "Статус", "Последняя ошибка"
            from v_research_runtime_state_grafana
            limit 1
            """,
        )

        research_status = str(research.get("Статус", "NO_DATA"))
        research_error = str(research.get("Последняя ошибка", ""))

        stats = _safe_row(
            conn,
            """
            select
                "Сделок",
                "PF",
                "Winrate",
                "Expectancy",
                "Статус стратегии"
            from v_strategy_statistics_futures_grafana
            where "Контракт" = %s
              and "Стратегия" = %s
              and "Таймфрейм" = %s
            order by "Обновлено" desc
            limit 1
            """,
            (symbol, strategy, timeframe),
        )

        promotion = _safe_row(
            conn,
            """
            select
                "Решение",
                "Разрешён runtime",
                "Разрешён research",
                "Причина"
            from v_strategy_promotion_decisions_grafana
            where "Инструмент" = %s
              and "Стратегия" = %s
              and "Таймфрейм" = %s
            order by "Время решения" desc
            limit 1
            """,
            (symbol, strategy, timeframe),
        )

        lifecycle = _safe_row(
            conn,
            """
            select
                "Состояние",
                "Разрешён runtime",
                "Разрешён research",
                "Причина"
            from v_strategy_lifecycle_grafana
            where "Инструмент" = %s
              and "Стратегия" = %s
              and "Таймфрейм" = %s
            order by "Обновлено" desc
            limit 1
            """,
            (symbol, strategy, timeframe),
        )

        trades = _to_int(stats.get("Сделок"), 0)
        pf = _to_float(stats.get("PF"), 0.0)
        winrate = _to_float(stats.get("Winrate"), 0.0)
        expectancy = _to_float(stats.get("Expectancy"), 0.0)
        strategy_status = str(stats.get("Статус стратегии", "NO_DATA"))

        promotion_decision = str(promotion.get("Решение", "NO_DATA"))
        lifecycle_state = str(lifecycle.get("Состояние", "NO_DATA"))

        allow_runtime = _to_bool(lifecycle.get("Разрешён runtime", promotion.get("Разрешён runtime", False)))
        allow_research = _to_bool(lifecycle.get("Разрешён research", promotion.get("Разрешён research", False)))

        reason = str(
            lifecycle.get("Причина")
            or promotion.get("Причина")
            or "нет причины / нет данных"
        )

        final_verdict = build_final_verdict(
            production_status=production_status,
            research_status=research_status,
            strategy_status=strategy_status,
            lifecycle_state=lifecycle_state,
            allow_runtime=allow_runtime,
            allow_research=allow_research,
            expectancy=expectancy,
            pf=pf,
            trades=trades,
        )

        return UnifiedResearchSnapshot(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
            production_status=production_status,
            projection_lag=projection_lag,
            dlq_unresolved=dlq_unresolved,
            research_supervisor_status=research_status,
            research_last_error=research_error,
            trades=trades,
            profit_factor=pf,
            winrate=winrate,
            expectancy=expectancy,
            strategy_status=strategy_status,
            promotion_decision=promotion_decision,
            lifecycle_state=lifecycle_state,
            allow_runtime=allow_runtime,
            allow_research=allow_research,
            reason=reason,
            final_verdict=final_verdict,
        )
    finally:
        conn.close()


def build_final_verdict(
    production_status: str,
    research_status: str,
    strategy_status: str,
    lifecycle_state: str,
    allow_runtime: bool,
    allow_research: bool,
    expectancy: float,
    pf: float,
    trades: int,
) -> str:
    # Русский комментарий:
    # Итоговый статус разделяет здоровье ядра, состояние research supervisor и качество стратегии.
    if production_status != "OK":
        return "СИСТЕМА_ТРЕБУЕТ_ВНИМАНИЯ"

    if research_status == "FAILED":
        return "RESEARCH_SUPERVISOR_FAILED"

    if lifecycle_state == "BLOCKED" or not allow_research:
        return "СТРАТЕГИЯ_ЗАБЛОКИРОВАНА"

    if trades < 30:
        return "МАЛАЯ_ВЫБОРКА_ОСТАВИТЬ_RESEARCH"

    if strategy_status in {"WEAK", "LOW_SAMPLE"} or expectancy <= 0 or pf < 1.0:
        return "СЛАБАЯ_СТАТИСТИКА_ОСТАВИТЬ_RESEARCH"

    if allow_runtime:
        return "КАНДИДАТ_В_RUNTIME"

    return "RESEARCH_OK_RUNTIME_НЕ_РАЗРЕШЕН"


def render_report(s: UnifiedResearchSnapshot) -> str:
    return f"""
========================================
 FINAM_CORE — ЕДИНАЯ RESEARCH-ТЕЛЕМЕТРИЯ
========================================

Инструмент                  : {s.symbol}
Стратегия                   : {s.strategy}
Таймфрейм                   : {s.timeframe}

----------------------------------------
ЗДОРОВЬЕ СИСТЕМЫ
----------------------------------------

Production health            : {s.production_status}
Projection lag               : {s.projection_lag}
DLQ unresolved               : {s.dlq_unresolved}

----------------------------------------
RESEARCH RUNTIME
----------------------------------------

Research supervisor          : {s.research_supervisor_status}
Последняя ошибка             : {s.research_last_error}

----------------------------------------
СТАТИСТИКА СТРАТЕГИИ
----------------------------------------

Сделок                       : {s.trades}
Profit Factor                : {s.profit_factor:.4f}
Winrate                      : {s.winrate:.4f}
Expectancy                   : {s.expectancy:.6f}
Статус стратегии             : {s.strategy_status}

----------------------------------------
ЖИЗНЕННЫЙ ЦИКЛ
----------------------------------------

Promotion decision           : {s.promotion_decision}
Lifecycle state              : {s.lifecycle_state}
Разрешён runtime             : {s.allow_runtime}
Разрешён research            : {s.allow_research}
Причина                      : {s.reason}

----------------------------------------
ИТОГ
----------------------------------------

{s.final_verdict}

========================================
""".strip()


def demo_snapshot() -> UnifiedResearchSnapshot:
    return UnifiedResearchSnapshot(
        symbol="BRM6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        production_status="OK",
        projection_lag=0,
        dlq_unresolved=0,
        research_supervisor_status="FAILED",
        research_last_error="orchestrator_failed",
        trades=119,
        profit_factor=0.9525,
        winrate=0.3613,
        expectancy=-0.140871,
        strategy_status="WEAK",
        promotion_decision="BLOCK",
        lifecycle_state="BLOCKED",
        allow_runtime=False,
        allow_research=False,
        reason="слабый_rank_status:REJECT",
        final_verdict="RESEARCH_SUPERVISOR_FAILED",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=os.getenv("SYMBOL", "BRM6@RTSX"))
    parser.add_argument("--strategy", default=os.getenv("STRATEGY", "BR_CONSERVATIVE_BREAKOUT"))
    parser.add_argument("--timeframe", default=os.getenv("TIMEFRAME", "M5"))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    snapshot = demo_snapshot() if args.demo else load_snapshot_from_postgres(
        symbol=args.symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
    )
    print(render_report(snapshot))


if __name__ == "__main__":
    main()
