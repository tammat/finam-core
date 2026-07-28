from __future__ import annotations

import os

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS guard_decision_report_v1 (
            id BIGSERIAL PRIMARY KEY,

            symbol TEXT,
            strategy TEXT,
            timeframe TEXT,
            session_type TEXT,
            regime TEXT,
            volatility_regime TEXT,

            signals_total BIGINT,
            filled_total BIGINT,
            closed_total BIGINT,

            wins BIGINT,
            losses BIGINT,
            flats BIGINT,

            winrate DOUBLE PRECISION,
            net_pnl DOUBLE PRECISION,
            profit_factor DOUBLE PRECISION,
            expectancy DOUBLE PRECISION,

            avg_confidence DOUBLE PRECISION,
            avg_rr DOUBLE PRECISION,
            avg_size_multiplier DOUBLE PRECISION,

            guard_decision TEXT NOT NULL,
            guard_reason TEXT NOT NULL,

            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime
            )
        );
        """)

        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_guard_decision_report_v1_decision
        ON guard_decision_report_v1(guard_decision);
        """)

    conn.commit()


def classify(
    *,
    closed_total: int,
    profit_factor: float | None,
    expectancy: float | None,
    winrate: float | None,
):
    if closed_total < 30:
        return (
            "INSUFFICIENT_DATA",
            f"closed_total={closed_total}<30",
        )

    pf = profit_factor or 0.0
    exp = expectancy or 0.0
    wr = winrate or 0.0

    # Русский комментарий: полностью запрещаем отрицательное математическое ожидание.
    if exp < 0 or pf < 0.95:
        return (
            "BLOCK",
            f"negative_edge expectancy={exp:.4f} pf={pf:.4f}",
        )

    # Русский комментарий: пограничные группы только под наблюдение.
    if pf < 1.10 or wr < 0.45:
        return (
            "WATCH",
            f"weak_edge winrate={wr:.4f} pf={pf:.4f}",
        )

    # Русский комментарий: хороший подтвержденный edge.
    return (
        "ALLOW",
        f"validated_edge expectancy={exp:.4f} pf={pf:.4f}",
    )


def build(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("""
        SELECT
            symbol,
            strategy,
            timeframe,
            session_type,
            regime,
            volatility_regime,

            signals_total,
            filled_total,
            closed_total,

            wins,
            losses,
            flats,

            winrate,
            net_pnl,
            profit_factor,
            expectancy,

            avg_confidence,
            avg_rr,
            avg_size_multiplier
        FROM signal_quality_aggregation_v1
        """)

        rows = cur.fetchall()
        observed_contracts = {
            (
                str(row[0] or "").upper(),
                str(row[1] or "").upper(),
                str(row[2] or "").upper(),
            )
            for row in rows
        }

        # Назначенная стратегия должна иметь явное решение guard даже до
        # появления первой сделки. Иначе loader возвращает NO_RULE, хотя
        # корректное состояние такого контракта — INSUFFICIENT_DATA.
        cur.execute("""
        SELECT
            symbol,
            strategy_code,
            timeframe
        FROM analytics.runtime_strategy_assignment_v1
        WHERE enabled IS TRUE
        """)
        for symbol, strategy, timeframe in cur.fetchall():
            contract = (
                str(symbol or "").upper(),
                str(strategy or "").upper(),
                str(timeframe or "").upper(),
            )
            if contract in observed_contracts:
                continue
            rows.append((
                symbol,
                strategy,
                timeframe,
                "UNKNOWN",
                "UNKNOWN",
                "UNKNOWN",
                0,
                0,
                0,
                0,
                0,
                0,
                None,
                0.0,
                None,
                None,
                None,
                None,
                None,
            ))

        # Режимная политика может назначать инструменту несколько исполнимых
        # стратегий (например, возврат к среднему в боковике и пробой в тренде).
        # Каждая ветка обязана получить явное guard-решение. Без этой выборки
        # вторая стратегия ошибочно превращалась в NO_RULE, хотя была назначена
        # действующей DB-политикой.
        cur.execute("""
        SELECT DISTINCT
            symbol,
            strategy_code,
            timeframe
        FROM analytics.runtime_strategy_policy_v2
        WHERE enabled IS TRUE
        """)
        for symbol, strategy, timeframe in cur.fetchall():
            contract = (
                str(symbol or "").upper(),
                str(strategy or "").upper(),
                str(timeframe or "").upper(),
            )
            if contract in observed_contracts:
                continue
            observed_contracts.add(contract)
            rows.append((
                symbol,
                strategy,
                timeframe,
                "UNKNOWN",
                "UNKNOWN",
                "UNKNOWN",
                0,
                0,
                0,
                0,
                0,
                0,
                None,
                0.0,
                None,
                None,
                None,
                None,
                None,
            ))

    saved = 0

    with conn.cursor() as cur:
        for row in rows:
            (
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime,
                signals_total,
                filled_total,
                closed_total,
                wins,
                losses,
                flats,
                winrate,
                net_pnl,
                profit_factor,
                expectancy,
                avg_confidence,
                avg_rr,
                avg_size_multiplier,
            ) = row

            decision, reason = classify(
                closed_total=closed_total or 0,
                profit_factor=profit_factor,
                expectancy=expectancy,
                winrate=winrate,
            )

            cur.execute("""
            INSERT INTO guard_decision_report_v1 (
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime,

                signals_total,
                filled_total,
                closed_total,

                wins,
                losses,
                flats,

                winrate,
                net_pnl,
                profit_factor,
                expectancy,

                avg_confidence,
                avg_rr,
                avg_size_multiplier,

                guard_decision,
                guard_reason,
                calculated_at
            )
            VALUES (
                %s,%s,%s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,
                %s,%s,%s,%s,
                %s,%s,%s,
                %s,%s,
                now()
            )
            ON CONFLICT (
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime
            )
            DO UPDATE SET
                signals_total = excluded.signals_total,
                filled_total = excluded.filled_total,
                closed_total = excluded.closed_total,
                wins = excluded.wins,
                losses = excluded.losses,
                flats = excluded.flats,
                winrate = excluded.winrate,
                net_pnl = excluded.net_pnl,
                profit_factor = excluded.profit_factor,
                expectancy = excluded.expectancy,
                avg_confidence = excluded.avg_confidence,
                avg_rr = excluded.avg_rr,
                avg_size_multiplier = excluded.avg_size_multiplier,
                guard_decision = excluded.guard_decision,
                guard_reason = excluded.guard_reason,
                calculated_at = now();
            """, (
                symbol,
                strategy,
                timeframe,
                session_type,
                regime,
                volatility_regime,

                signals_total,
                filled_total,
                closed_total,

                wins,
                losses,
                flats,

                winrate,
                net_pnl,
                profit_factor,
                expectancy,

                avg_confidence,
                avg_rr,
                avg_size_multiplier,

                decision,
                reason,
            ))

            saved += 1

    conn.commit()
    return saved


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        migrate(conn)
        saved = build(conn)

    print(f"GUARD_DECISION_REPORT_V1_OK saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
