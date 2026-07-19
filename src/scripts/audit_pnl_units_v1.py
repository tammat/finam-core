from __future__ import annotations

import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
NAMESPACE = uuid.UUID("aa031461-ce36-42ef-98d5-4ce11d6bc44c")


def asset_class(symbol: str) -> str:
    if symbol.endswith("@RTSX"):
        return "FUTURES"
    if symbol.endswith("@MISX"):
        return "EQUITY"
    if symbol.endswith("USD"):
        return "CRYPTO"
    return "OTHER"


def main() -> int:
    scenario_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    ready = blocked = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT symbol FROM public.market_bars
              WHERE timeframe='M5' AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
              GROUP BY symbol HAVING count(*)>=6000
              UNION SELECT DISTINCT ON(root_symbol) selected_symbol
              FROM analytics.futures_roll_decision_v1
              WHERE selected_symbol IS NOT NULL ORDER BY symbol""")
            symbols = [str(row["symbol"]) for row in cursor.fetchall() if row["symbol"]]
            for symbol in symbols:
                kind = asset_class(symbol)
                cursor.execute("""SELECT s.lot_size,s.tick_size,s.tick_value,s.contract_multiplier,
                      x.quantity_step,x.underlying_units,s.source_version
                    FROM analytics.market_contract_spec_v1 s
                    LEFT JOIN analytics.market_contract_execution_spec_v2 x ON x.symbol=%s
                    WHERE s.is_active AND (s.symbol=%s OR
                      (%s LIKE 'BR%%@RTSX' AND s.symbol='BR@RTSX') OR
                      (%s LIKE 'NG%%@RTSX' AND s.symbol='NG@RTSX'))
                    ORDER BY (s.symbol=%s) DESC,s.valid_from DESC LIMIT 1""",
                    (symbol,symbol,symbol,symbol,symbol))
                spec = cursor.fetchone() or {}
                cursor.execute("""SELECT initial_margin,maintenance_margin,currency,source
                    FROM public.margin_requirements WHERE active AND symbol=%s
                    ORDER BY updated_at DESC LIMIT 1""", (symbol,))
                margin = cursor.fetchone() or {}
                lot = float(spec.get("lot_size") or 0)
                tick_size = float(spec.get("tick_size") or 0)
                tick_value = float(spec.get("tick_value") or 0)
                multiplier = float(spec.get("contract_multiplier") or 0)
                quantity_step = float(spec.get("quantity_step") or 0)
                underlying = float(spec.get("underlying_units") or 0)
                expected_tick = tick_size * multiplier
                checks = {
                    "specification_present": bool(spec),
                    "positive_lot": lot > 0,
                    "positive_tick": tick_size > 0 and tick_value > 0,
                    "positive_multiplier": multiplier > 0,
                    "positive_quantity_step": quantity_step > 0,
                    "tick_identity": expected_tick > 0 and abs(tick_value-expected_tick) / expected_tick <= 0.01,
                    "margin_present": kind != "FUTURES" or float(margin.get("initial_margin") or 0) > 0,
                }
                reasons = [name.upper() for name, passed in checks.items() if not passed]
                status = "READY" if not reasons else "BLOCKED"
                audit_id = uuid.uuid5(NAMESPACE, f"{scenario_run_id}:{symbol}")
                cursor.execute("""INSERT INTO analytics.pnl_unit_audit_v1
                    (audit_id,scenario_run_id,symbol,asset_class,lot_size,tick_size,tick_value,
                     contract_multiplier,quantity_step,underlying_units,margin_currency,
                     check_results,status_code,reason_codes)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(scenario_run_id,symbol) DO UPDATE SET
                     check_results=EXCLUDED.check_results,status_code=EXCLUDED.status_code,
                     reason_codes=EXCLUDED.reason_codes,audited_at=clock_timestamp()""",
                    (str(audit_id),scenario_run_id,symbol,kind,lot or None,tick_size or None,
                     tick_value or None,multiplier or None,quantity_step or None,underlying or None,
                     margin.get("currency"),psycopg2.extras.Json(checks),status,
                     psycopg2.extras.Json(reasons)))
                ready += int(status == "READY")
                blocked += int(status == "BLOCKED")
    print(f"pnl_units_ready={ready}")
    print(f"pnl_units_blocked={blocked}")
    print("VERDICT=PNL_UNIT_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
