from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "ECONOMIC_HYPOTHESES_V1_DB_DRIVEN"


def dynamic(grid: list[dict]) -> list[dict]:
    output = []
    for item in grid:
        output.append({**item,"entry_policy_code":"META_ENTRY_V2","entry_profile_code":"AUTO_BY_MARKET",
                       "exit_policy_code":"DYNAMIC_EXIT_V1",
                       "exit_max_holding_bars":20,"exit_atr_lookback":14,
                       "exit_stop_atr":2.0,"exit_trail_atr":2.5,
                       "exit_trend_lookback":20,"exit_volatility_lookback":20,
                       "exit_volatility_risk_multiplier":3.0})
    return output


def main() -> int:
    created = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT gate_policy FROM analytics.edge_search_algorithm_registry_v1
                WHERE algorithm_code='RELATIVE_STRENGTH'""")
            template = cursor.fetchone()
            if not template:
                raise RuntimeError("ECONOMIC_HYPOTHESIS_GATE_TEMPLATE_MISSING")
            gate = template["gate_policy"]
            cursor.execute("""WITH latest AS (
                SELECT run_id FROM analytics.edge_research_universe_snapshot_v1
                WHERE stage_code='WALKFORWARD' ORDER BY created_at DESC LIMIT 1)
              SELECT array_agg(symbol ORDER BY symbol) symbols
              FROM analytics.edge_research_universe_snapshot_v1
              WHERE run_id=(SELECT run_id FROM latest) AND selected AND symbol LIKE '%%@MISX'""")
            equities = list((cursor.fetchone() or {}).get("symbols") or [])
            configurations = []
            if equities:
                configurations.extend([
                    ("EQUITY_CROSS_SECTION_MOMENTUM","RELATIVE_STRENGTH_V1",
                     dynamic([{"lookback":40,"hold":12,"threshold":0.5},
                              {"lookback":80,"hold":20,"threshold":1.0}]),
                     {"target_symbols":equities,"reference_symbol":"IMOEX2",
                      "economic_hypothesis":"EQUITY_CROSS_SECTION_MOMENTUM",
                      "allowed_regimes":["trend_up","trend_down","range_normal"]}),
                    ("EQUITY_LIQUIDITY_REVERSION","LIQUIDITY_SHOCK_REVERSION_V1",
                     dynamic([{"lookback":40,"hold":8,"threshold":2.0,"volume_multiple":2.0},
                              {"lookback":80,"hold":12,"threshold":2.5,"volume_multiple":1.5}]),
                     {"target_symbols":equities,"economic_hypothesis":"EQUITY_LIQUIDITY_REVERSION",
                      "allowed_regimes":["range_normal","range_compression","compression"]}),
                    ("EQUITY_EVENT_GAP","SESSION_GAP_CONTINUATION_V1",
                     dynamic([{"lookback":40,"hold":12,"threshold":1.5,"minimum_gap_hours":6},
                              {"lookback":80,"hold":20,"threshold":2.0,"minimum_gap_hours":6}]),
                     {"target_symbols":equities,"economic_hypothesis":"EQUITY_EVENT_GAP",
                      "allowed_regimes":["trend_up","trend_down","trend_up_expansion","trend_down_expansion"]}),
                ])
                if "SBER@MISX" in equities:
                    configurations.append(("CROSS_ASSET_SBER_SPREAD","INTERMARKET_SPREAD_REVERSION_V1",
                        dynamic([{"lookback":40,"hold":8,"threshold":1.5},
                                 {"lookback":80,"hold":12,"threshold":2.0}]),
                        {"target_symbols":["SBER@MISX"],"reference_symbol":"SBERP@MISX",
                         "economic_hypothesis":"CROSS_ASSET_RELATIVE_VALUE",
                         "allowed_regimes":["range_normal","range_compression","compression"]}))
            cursor.execute("""SELECT DISTINCT ON(root_symbol) root_symbol,selected_symbol,next_symbol
                FROM analytics.futures_roll_decision_v1
                WHERE selected_symbol IS NOT NULL AND next_symbol IS NOT NULL
                  AND selected_symbol<>next_symbol
                ORDER BY root_symbol,created_at DESC""")
            for roll in cursor.fetchall():
                root = str(roll["root_symbol"])
                target = str(roll["selected_symbol"])
                reference = str(roll["next_symbol"])
                configurations.extend([
                    (f"FUTURES_CARRY_{root}","FUTURES_CURVE_CARRY_V1",
                     dynamic([{"lookback":40,"hold":12,"threshold":0.10},
                              {"lookback":80,"hold":20,"threshold":0.20}]),
                     {"target_symbols":[target],"reference_symbol":reference,
                      "economic_hypothesis":"FUTURES_CARRY_ROLL","contract_root":root,
                      "allowed_regimes":["trend_up","trend_down","range_normal","compression"]}),
                    (f"FUTURES_SEASONALITY_{root}","CALENDAR_SEASONALITY_V1",
                     dynamic([{"lookback":480,"hold":12,"threshold":2.0,"min_calendar_samples":4},
                              {"lookback":960,"hold":20,"threshold":3.0,"min_calendar_samples":6}]),
                     {"target_symbols":[target],"economic_hypothesis":"FUTURES_CALENDAR_SEASONALITY",
                      "contract_root":root,
                      "allowed_regimes":["trend_up","trend_down","range_normal","compression"]}),
                ])
            for algorithm,strategy,grid,regime in configurations:
                cursor.execute("""INSERT INTO analytics.edge_search_algorithm_registry_v1
                    (algorithm_code,strategy_code,enabled,parameter_grid,regime_policy,gate_policy,config_version)
                    VALUES(%s,%s,true,%s,%s,%s,%s)
                    ON CONFLICT(algorithm_code) DO UPDATE SET strategy_code=EXCLUDED.strategy_code,
                      enabled=true,parameter_grid=EXCLUDED.parameter_grid,regime_policy=EXCLUDED.regime_policy,
                      gate_policy=EXCLUDED.gate_policy,config_version=EXCLUDED.config_version,
                      updated_at=clock_timestamp()""",
                    (algorithm,strategy,psycopg2.extras.Json(grid),psycopg2.extras.Json(regime),
                     psycopg2.extras.Json(gate),VERSION))
                created += 1
    print(f"economic_algorithms_active={created}")
    print("asset_scope=EQUITY,FUTURES")
    print("VERDICT=ECONOMIC_HYPOTHESIS_SYNC_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
