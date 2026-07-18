from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "SWING_NEXT_RESEARCH_PLAN_V1"
NAMESPACE = uuid.UUID("62440f72-d658-53df-bba1-10d80c78bc3b")


def adaptation(reason: str) -> tuple[str, str]:
    return {
        "INSUFFICIENT_SELECTION_TRADES": ("EXPAND_HISTORY", "Накопить больше независимой истории."),
        "SELECTION_EDGE_FAILED": ("REJECT_REGION", "Исключить область без преимущества на выборке отбора."),
        "INSUFFICIENT_VALIDATION_TRADES": ("EXPAND_FUTURE_WINDOW", "Дождаться достаточного числа будущих сделок."),
        "VALIDATION_EDGE_FAILED": ("REJECT_REGION", "Исключить область без преимущества на валидации."),
        "VALIDATION_FOLDS_UNSTABLE": ("REFINE_REGIME", "Разделить рыночные режимы и повторить на будущих данных."),
        "MULTIPLE_TESTING_SIGNIFICANCE_FAILED": ("REDUCE_HYPOTHESIS_FAMILY", "Сократить семейство гипотез и накопить независимые наблюдения."),
    }.get(reason, ("REVIEW", "Провести дополнительную независимую проверку."))

def confirmation_contract(timeframe: str) -> tuple[datetime, int]:
    days,bars={"H1":(4,50),"H4":(10,30),"D1":(30,20)}[timeframe]
    return datetime.now(timezone.utc)+timedelta(days=days),bars


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT validation_run_id,factory_run_id FROM analytics.swing_selection_validation_result_v1
                ORDER BY created_at DESC LIMIT 1""")
            source = cursor.fetchone()
            if not source:
                print("VERDICT=SWING_NEXT_PLAN_WAITING_FOR_VALIDATION")
                return 0
            plan_id = uuid.uuid5(NAMESPACE, f"{source['validation_run_id']}:{VERSION}")
            cursor.execute("SELECT 1 FROM analytics.swing_next_research_plan_v1 WHERE plan_id=%s", (str(plan_id),))
            if cursor.fetchone():
                print(f"plan_id={plan_id}")
                print("VERDICT=SWING_NEXT_PLAN_ALREADY_EXISTS")
                return 0
            cursor.execute("""SELECT r.*,h.parameter_json FROM analytics.swing_selection_validation_result_v1 r
                JOIN analytics.swing_hypothesis_factory_v1 h
                  ON h.factory_run_id=r.factory_run_id AND h.hypothesis_id=r.hypothesis_id
                WHERE r.validation_run_id=%s AND r.validation_status='VALIDATION_FAIL'
                  AND r.selection_pf>=1.05 AND r.selection_expectancy>0
                  AND r.validation_pf>=1.05 AND r.validation_expectancy>0
                ORDER BY r.validation_folds_passed DESC,r.adjusted_p_value,
                         r.validation_pf DESC,r.validation_expectancy DESC,r.hypothesis_id
                LIMIT 12""", (str(source["validation_run_id"]),))
            candidates = cursor.fetchall()
            reasons = {}
            for row in candidates:
                reasons[row["reason_code"]] = reasons.get(row["reason_code"],0)+1
            cursor.execute("""INSERT INTO analytics.swing_next_research_plan_v1
                (plan_id,source_validation_run_id,source_factory_run_id,generator_version,status_code,
                 item_count,reason_summary,confirmation_mode,pass_gates_unchanged)
                VALUES(%s,%s,%s,%s,'WAITING_FUTURE_DATA',%s,%s,'FUTURE_DATA_ONLY',true)""",
                (str(plan_id),str(source["validation_run_id"]),str(source["factory_run_id"]),VERSION,
                 len(candidates),psycopg2.extras.Json(reasons)))
            for priority,row in enumerate(candidates,1):
                code,rationale = adaptation(row["reason_code"])
                confirmation_after,minimum_future_bars=confirmation_contract(row["timeframe"])
                item_id = uuid.uuid5(NAMESPACE,f"{plan_id}:{row['hypothesis_id']}")
                cursor.execute("""INSERT INTO analytics.swing_next_research_plan_item_v1
                    (plan_item_id,plan_id,priority,hypothesis_id,strategy_family,symbol,timeframe,
                     source_reason_code,adaptation_code,parameter_snapshot,status_code,rationale_ru,
                     confirmation_after_ts,minimum_future_bars)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'WAITING_FUTURE_DATA',%s,%s,%s)""",
                    (str(item_id),str(plan_id),priority,str(row["hypothesis_id"]),row["strategy_family"],
                     row["symbol"],row["timeframe"],row["reason_code"],code,
                     psycopg2.extras.Json(row["parameter_json"]),rationale,confirmation_after,minimum_future_bars))
    print(f"plan_id={plan_id}")
    print(f"items={len(candidates)}")
    print("confirmation_mode=FUTURE_DATA_ONLY")
    print("pass_gates=UNCHANGED")
    print("final_oos_opened=0")
    print("live_allowed=0")
    print("VERDICT=SWING_NEXT_RESEARCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
