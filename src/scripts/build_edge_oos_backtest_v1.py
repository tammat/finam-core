from __future__ import annotations

import os
import uuid
from statistics import mean

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_OOS_BACKTEST_V1"


def profit_factor(values: list[float]) -> float:
    pos = sum(v for v in values if v > 0)
    neg = abs(sum(v for v in values if v < 0))

    if neg == 0 and pos > 0:
        return 999.0
    if neg == 0:
        return 0.0
    return pos / neg


def winrate(values: list[float]) -> float:
    if not values:
        return 0.0
    wins = sum(1 for v in values if v > 0)
    return wins / len(values)


def pnl(values: list[float]) -> float:
    return sum(values) if values else 0.0


def expectancy(values: list[float]) -> float:
    return mean(values) if values else 0.0


def metrics(values: list[float]) -> dict:
    return {
        "trades": len(values),
        "pnl": pnl(values),
        "expectancy": expectancy(values),
        "profit_factor": profit_factor(values),
        "winrate": winrate(values),
    }


def classify(row: dict, is_metrics: dict, oos_metrics: dict) -> dict:
    total_trades = is_metrics["trades"] + oos_metrics["trades"]
    oos_status = str(row.get("oos_status") or "UNKNOWN")
    oos_readiness = str(row.get("oos_readiness") or "UNKNOWN")

    score = 0.0
    if oos_metrics["trades"] >= 10:
        score += 0.20
    if oos_metrics["expectancy"] > 0:
        score += 0.30
    if oos_metrics["profit_factor"] >= 1.0:
        score += 0.25
    if oos_metrics["winrate"] >= 0.45:
        score += 0.15
    if is_metrics["expectancy"] > 0:
        score += 0.10

    if total_trades < 30:
        return {
            "backtest_status": "WAIT_SAMPLE",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "",
            "fail_reason": "Недостаточная общая выборка для OOS backtest.",
            "recommended_action": "Накопить выборку Paper Runtime.",
        }

    if oos_metrics["trades"] < 10:
        return {
            "backtest_status": "WAIT_OOS_SAMPLE",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "",
            "fail_reason": "Недостаточная OOS-выборка.",
            "recommended_action": "Продолжить накопление свежих OOS-сделок.",
        }

    if oos_status != "READY_FOR_OOS" and oos_readiness != "READY":
        return {
            "backtest_status": "NOT_READY_FROM_OOS_GATE",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "",
            "fail_reason": "Кандидат не получил статус READY_FOR_OOS.",
            "recommended_action": "Вернуть в robustness/OOS preparation.",
        }

    if oos_metrics["expectancy"] > 0 and oos_metrics["profit_factor"] >= 1.0 and score >= 0.70:
        return {
            "backtest_status": "OOS_PASS",
            "stability_score": score,
            "micro_live_candidate": False,
            "pass_reason": "OOS expectancy положительное, PF >= 1.0, stability score достаточный.",
            "fail_reason": "",
            "recommended_action": "Передать в MICRO_LIVE_READINESS_V1 после финальной риск-проверки.",
        }

    return {
        "backtest_status": "OOS_FAIL",
        "stability_score": score,
        "micro_live_candidate": False,
        "pass_reason": "",
        "fail_reason": "OOS-метрики не подтверждают устойчивость edge.",
        "recommended_action": "Не продвигать кандидата без дополнительного анализа.",
    }


def load_trade_pnl(cur, symbol: str, strategy: str, timeframe: str) -> list[float]:
    cur.execute(
        """
        SELECT
            COALESCE(closed_at, exit_ts, created_at) AS ts,
            net_pnl
        FROM public.closed_trades
        WHERE trade_source='paper'
          AND (%s = '' OR symbol=%s)
          AND (%s = '' OR strategy=%s)
          AND (%s = '' OR timeframe=%s)
          AND net_pnl IS NOT NULL
        ORDER BY COALESCE(closed_at, exit_ts, created_at) ASC NULLS LAST;
        """,
        (symbol, symbol, strategy, strategy, timeframe, timeframe),
    )
    rows = cur.fetchall()
    return [float(row["net_pnl"]) for row in rows if row["net_pnl"] is not None]


def split_is_oos(values: list[float]) -> tuple[list[float], list[float]]:
    if len(values) <= 1:
        return values, []
    split_at = max(1, int(len(values) * 0.70))
    return values[:split_at], values[split_at:]


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("=== EDGE_OOS_BACKTEST_V1 ===")

            cur.execute(
                """
                SELECT
                    oos_rank,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    robustness_status,
                    oos_status,
                    oos_readiness
                FROM marketcore_ui.edge_oos_validation_v1
                ORDER BY
                    CASE
                        WHEN oos_status='READY_FOR_OOS' THEN 1
                        WHEN oos_status='OBSERVE_MORE' THEN 2
                        WHEN oos_status='WAIT_SAMPLE' THEN 3
                        ELSE 4
                    END,
                    oos_rank;
                """
            )
            rows = [dict(row) for row in cur.fetchall()]

            cur.execute("DELETE FROM marketcore_ui.edge_oos_backtest_v1;")

            for idx, row in enumerate(rows, start=1):
                symbol = str(row.get("symbol") or "")
                strategy = str(row.get("strategy") or "")
                timeframe = str(row.get("timeframe") or "")
                side = str(row.get("side") or "")

                values = load_trade_pnl(cur, symbol=symbol, strategy=strategy, timeframe=timeframe)
                is_values, oos_values = split_is_oos(values)

                is_m = metrics(is_values)
                oos_m = metrics(oos_values)
                c = classify(row, is_m, oos_m)

                cur.execute(
                    """
                    INSERT INTO marketcore_ui.edge_oos_backtest_v1 (
                        backtest_rank,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        robustness_status,
                        oos_status,
                        oos_readiness,
                        backtest_status,
                        total_trades,
                        in_sample_trades,
                        oos_trades,
                        in_sample_pnl,
                        oos_pnl,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        in_sample_winrate,
                        oos_winrate,
                        stability_score,
                        micro_live_candidate,
                        pass_reason,
                        fail_reason,
                        recommended_action,
                        source_oos_rank,
                        source_version,
                        refreshed_at,
                        build_id
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                        %s,%s,%s,%s,%s,%s,%s,now(),%s
                    );
                    """,
                    (
                        idx,
                        symbol,
                        strategy,
                        timeframe,
                        side,
                        row.get("robustness_status") or "UNKNOWN",
                        row.get("oos_status") or "UNKNOWN",
                        row.get("oos_readiness") or "UNKNOWN",
                        c["backtest_status"],
                        len(values),
                        is_m["trades"],
                        oos_m["trades"],
                        is_m["pnl"],
                        oos_m["pnl"],
                        is_m["expectancy"],
                        oos_m["expectancy"],
                        is_m["profit_factor"],
                        oos_m["profit_factor"],
                        is_m["winrate"],
                        oos_m["winrate"],
                        c["stability_score"],
                        c["micro_live_candidate"],
                        c["pass_reason"],
                        c["fail_reason"],
                        c["recommended_action"],
                        row.get("oos_rank"),
                        SOURCE_VERSION,
                        build_id,
                    ),
                )

            cur.execute("SELECT count(*) AS rows FROM marketcore_ui.edge_oos_backtest_v1;")
            rows_written = int(cur.fetchone()["rows"])

            cur.execute(
                """
                SELECT backtest_status, count(*) AS rows
                FROM marketcore_ui.edge_oos_backtest_v1
                GROUP BY backtest_status
                ORDER BY backtest_status;
                """
            )
            status_rows = cur.fetchall()

    print(f"rows_written={rows_written}")
    for row in status_rows:
        print(f"backtest_status_{row['backtest_status']}={row['rows']}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_OOS_BACKTEST_V1_READY")


if __name__ == "__main__":
    main()
