from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "PAPER_EXECUTION_ANALYTICS_ENGINE_V1"


def dec(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def sample_status(trades: int, validated_min: int, production_min: int) -> str:
    if trades >= production_min:
        return "PRODUCTION"
    if trades >= validated_min:
        return "VALIDATED"
    return "RESEARCH"


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    trades = len(rows)
    wins = [r for r in rows if dec(r["r_multiple"]) > 0]
    losses = [r for r in rows if dec(r["r_multiple"]) < 0]
    flats = [r for r in rows if dec(r["r_multiple"]) == 0]

    gross_profit = sum((dec(r["pnl_points"]) for r in wins), Decimal("0"))
    gross_loss = abs(sum((dec(r["pnl_points"]) for r in losses), Decimal("0")))
    net = sum((dec(r["pnl_points"]) for r in rows), Decimal("0"))

    pf = None if gross_loss == 0 else gross_profit / gross_loss
    expectancy = None if trades == 0 else sum((dec(r["r_multiple"]) for r in rows), Decimal("0")) / Decimal(trades)
    win_rate = None if trades == 0 else Decimal(len(wins)) / Decimal(trades)
    avg_r = expectancy
    avg_mae = None if trades == 0 else sum((dec(r["mae_points"]) for r in rows), Decimal("0")) / Decimal(trades)
    avg_mfe = None if trades == 0 else sum((dec(r["mfe_points"]) for r in rows), Decimal("0")) / Decimal(trades)
    avg_bars = None if trades == 0 else sum((dec(r["bars_held"]) for r in rows), Decimal("0")) / Decimal(trades)

    return {
        "trades_total": trades,
        "wins_total": len(wins),
        "losses_total": len(losses),
        "flat_total": len(flats),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl_points": net,
        "profit_factor": pf,
        "expectancy_r": expectancy,
        "win_rate": win_rate,
        "avg_r_multiple": avg_r,
        "avg_mae_points": avg_mae,
        "avg_mfe_points": avg_mfe,
        "avg_bars_held": avg_bars,
    }


def insert_metric_row(cur, table: str, snapshot_id: int, extra_cols: dict[str, Any], m: dict[str, Any], status: str | None) -> None:
    cols = ["analytics_snapshot_id", *extra_cols.keys(), *m.keys()]
    vals = [snapshot_id, *extra_cols.values(), *m.values()]

    if status is not None:
        cols.append("sample_status")
        vals.append(status)

    cols.append("source_version")
    vals.append(SOURCE_VERSION)

    placeholders = ",".join(["%s"] * len(vals))
    cur.execute(
        f"""
        INSERT INTO analytics.{table}
        ({",".join(cols)})
        VALUES ({placeholders})
        """,
        vals,
    )


def group_by(rows: list[dict[str, Any]], key_fn) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    result: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        key = key_fn(row)
        result.setdefault(key, []).append(row)
    return result


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT parameter_value FROM knowledge.platform_parameter_v1 WHERE parameter_code='PAPER_ANALYTICS_VALIDATED_MIN_TRADES' AND enabled")
            validated_min = int(dec(cur.fetchone()["parameter_value"]))

            cur.execute("SELECT parameter_value FROM knowledge.platform_parameter_v1 WHERE parameter_code='PAPER_ANALYTICS_PRODUCTION_MIN_TRADES' AND enabled")
            production_min = int(dec(cur.fetchone()["parameter_value"]))

            cur.execute(
                """
                INSERT INTO analytics.analytics_snapshot_v1
                (snapshot_type, source_version, evidence_json)
                VALUES (%s,%s,%s::jsonb)
                RETURNING analytics_snapshot_id
                """,
                (
                    "PAPER_EXECUTION_ANALYTICS",
                    SOURCE_VERSION,
                    json.dumps(
                        {
                            "paper_result_source_version": "PAPER_EXECUTION_SIMULATOR_V1",
                            "validated_min_trades": validated_min,
                            "production_min_trades": production_min,
                            "overfit_guard": "sample_status_only_no_auto_decision",
                        },
                        ensure_ascii=False,
                    ),
                ),
            )
            snapshot_id = int(cur.fetchone()["analytics_snapshot_id"])

            cur.execute(
                """
                SELECT
                    p.*,
                    x.evidence_json AS trading_plan_evidence,
                    mc.regime_code
                FROM knowledge.paper_execution_result_v1 p
                JOIN knowledge.recommendation_execution_context_v1 x
                  ON x.execution_context_id=p.execution_context_id
                LEFT JOIN knowledge.market_context_v1 mc
                  ON mc.context_id=x.source_context_id
                WHERE p.source_version='PAPER_EXECUTION_SIMULATOR_V1'
                """
            )
            rows = [dict(r) for r in cur.fetchall()]

            summary = metrics(rows)
            insert_metric_row(
                cur,
                "paper_execution_summary_v1",
                snapshot_id,
                {},
                summary,
                None,
            )

            profile_groups = group_by(
                rows,
                lambda r: (str((r["trading_plan_evidence"] or {}).get("profile_code", "UNKNOWN")),),
            )
            for (profile_code,), group_rows in profile_groups.items():
                m = metrics(group_rows)
                insert_metric_row(
                    cur,
                    "paper_execution_profile_scorecard_v1",
                    snapshot_id,
                    {"profile_code": profile_code},
                    m,
                    sample_status(m["trades_total"], validated_min, production_min),
                )

            source_groups = group_by(
                rows,
                lambda r: (
                    str((r["trading_plan_evidence"] or {}).get("entry_source", "UNKNOWN")),
                    str((r["trading_plan_evidence"] or {}).get("stop_source", "UNKNOWN")),
                    str((r["trading_plan_evidence"] or {}).get("target_source", "UNKNOWN")),
                ),
            )
            for (entry_source, stop_source, target_source), group_rows in source_groups.items():
                m = metrics(group_rows)
                insert_metric_row(
                    cur,
                    "paper_execution_source_scorecard_v1",
                    snapshot_id,
                    {
                        "entry_source": entry_source,
                        "stop_source": stop_source,
                        "target_source": target_source,
                    },
                    m,
                    sample_status(m["trades_total"], validated_min, production_min),
                )

            regime_groups = group_by(
                rows,
                lambda r: (str(r.get("regime_code") or "UNKNOWN"),),
            )
            for (regime_code,), group_rows in regime_groups.items():
                m = metrics(group_rows)
                insert_metric_row(
                    cur,
                    "paper_execution_regime_scorecard_v1",
                    snapshot_id,
                    {"regime_code": regime_code},
                    m,
                    sample_status(m["trades_total"], validated_min, production_min),
                )

    print("=== PAPER_EXECUTION_ANALYTICS_ENGINE_V1 ===")
    print(f"analytics_snapshot_id={snapshot_id}")
    print(f"paper_rows_loaded={len(rows)}")
    print("summary_rows=1")
    print(f"profile_scorecard_rows={len(profile_groups)}")
    print(f"source_scorecard_rows={len(source_groups)}")
    print(f"regime_scorecard_rows={len(regime_groups)}")
    print("overfit_guard=sample_status_only")
    print("auto_decision=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PAPER_EXECUTION_ANALYTICS_ENGINE_V1_READY")


if __name__ == "__main__":
    main()
