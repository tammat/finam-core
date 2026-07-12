from __future__ import annotations

import itertools
import json
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
MAX_TRIALS = int(os.getenv("HYPOTHESIS_MAX_TRIALS", "5000"))
SOURCE_VERSION = "STRATEGY_FAMILY_REGISTRY_V2"

FAMILIES = {
    "MOMENTUM": {
        "name_ru": "Импульс",
        "engine": "REGIME_OOS_V2",
        "priority": 1,
        "parameters": {"lookback": [10, 20, 40, 60], "threshold": [0.003, 0.006, 0.01], "holding_bars": [3, 6, 12], "direction": ["LONG", "SHORT"]},
        "regimes": ["trend_up", "trend_down", "trend_up_expansion", "trend_down_expansion"],
    },
    "BREAKOUT": {
        "name_ru": "Пробой",
        "engine": "REGIME_OOS_V2",
        "priority": 2,
        "parameters": {"lookback": [12, 24, 48, 96], "threshold": [0.002, 0.004, 0.008], "holding_bars": [3, 6, 12], "confirmation_bars": [1, 2]},
        "regimes": ["compression", "trend_up_expansion", "trend_down_expansion"],
    },
    "MEAN_REVERSION": {
        "name_ru": "Возврат к среднему",
        "engine": "REGIME_OOS_V2",
        "priority": 3,
        "parameters": {"lookback": [12, 24, 48, 96], "entry_zscore": [1.0, 1.5, 2.0], "holding_bars": [3, 6, 12], "exit_zscore": [0.0, 0.5]},
        "regimes": ["range_normal", "range_compression", "compression"],
    },
    "RELATIVE_STRENGTH": {
        "name_ru": "Относительная сила",
        "engine": "RELATIONSHIP_FACTORY_V2",
        "priority": 4,
        "parameters": {"lookback": [12, 24, 48, 96], "rank_threshold": [0.6, 0.7, 0.8], "holding_bars": [3, 6, 12], "benchmark": ["IMOEX", "IMOEX2"]},
        "regimes": ["trend_up", "trend_down", "range_normal"],
    },
    "INTERMARKET_LEAD_LAG": {
        "name_ru": "Межрыночный Lead/Lag",
        "engine": "LEAD_LAG_V1",
        "priority": 5,
        "parameters": {"impulse_bars": [1, 3, 6, 12], "lag_bars": [1, 2, 3, 6], "threshold": [0.002, 0.004, 0.008], "holding_bars": [3, 6, 12]},
        "regimes": ["trend_up", "trend_down", "range_normal", "compression"],
    },
}


def combinations(parameter_grid: dict[str, list[object]]):
    keys = list(parameter_grid)
    for values in itertools.product(*(parameter_grid[key] for key in keys)):
        yield dict(zip(keys, values))


def main() -> None:
    run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics.strategy_family_registry_v2 (
                    strategy_family text PRIMARY KEY,
                    name_ru text NOT NULL,
                    engine_code text NOT NULL,
                    priority integer NOT NULL,
                    enabled boolean NOT NULL DEFAULT true,
                    allowed_regimes jsonb NOT NULL,
                    parameter_schema jsonb NOT NULL,
                    oos_required boolean NOT NULL DEFAULT true,
                    multiple_testing_required boolean NOT NULL DEFAULT true,
                    live_allowed boolean NOT NULL DEFAULT false,
                    source_version text NOT NULL,
                    updated_at timestamptz NOT NULL DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS analytics.hypothesis_parameter_space_v2 (
                    parameter_space_run_id uuid NOT NULL,
                    strategy_family text NOT NULL REFERENCES analytics.strategy_family_registry_v2(strategy_family),
                    parameter_json jsonb NOT NULL,
                    engine_code text NOT NULL,
                    candidate_hash text NOT NULL,
                    estimated_trials integer NOT NULL,
                    overfit_risk text NOT NULL,
                    enabled boolean NOT NULL DEFAULT true,
                    source_version text NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    PRIMARY KEY(parameter_space_run_id, candidate_hash)
                );
                CREATE INDEX IF NOT EXISTS hypothesis_parameter_space_v2_latest_idx
                    ON analytics.hypothesis_parameter_space_v2(created_at DESC, strategy_family);
            """)
            for family, definition in FAMILIES.items():
                cur.execute("""
                    INSERT INTO analytics.strategy_family_registry_v2
                    (strategy_family,name_ru,engine_code,priority,enabled,allowed_regimes,parameter_schema,
                     oos_required,multiple_testing_required,live_allowed,source_version,updated_at)
                    VALUES (%s,%s,%s,%s,true,%s,%s,true,true,false,%s,now())
                    ON CONFLICT(strategy_family) DO UPDATE SET
                      name_ru=excluded.name_ru,engine_code=excluded.engine_code,priority=excluded.priority,
                      allowed_regimes=excluded.allowed_regimes,parameter_schema=excluded.parameter_schema,
                      source_version=excluded.source_version,updated_at=now()
                """, (family, definition["name_ru"], definition["engine"], definition["priority"],
                      psycopg2.extras.Json(definition["regimes"]), psycopg2.extras.Json(definition["parameters"]), SOURCE_VERSION))

            all_candidates: list[tuple[str, dict[str, object], str]] = []
            for family, definition in FAMILIES.items():
                all_candidates.extend((family, params, str(definition["engine"])) for params in combinations(definition["parameters"]))
            selected = all_candidates[:MAX_TRIALS]
            for family, params, engine in selected:
                canonical = json.dumps({"family": family, "parameters": params}, sort_keys=True, ensure_ascii=False)
                cur.execute("""
                    INSERT INTO analytics.hypothesis_parameter_space_v2
                    (parameter_space_run_id,strategy_family,parameter_json,engine_code,candidate_hash,
                     estimated_trials,overfit_risk,enabled,source_version)
                    VALUES (%s,%s,%s,%s,md5(%s),%s,%s,true,%s)
                """, (run_id, family, psycopg2.extras.Json(params), engine, canonical, len(selected),
                      "CONTROLLED" if len(selected) <= MAX_TRIALS else "HIGH", SOURCE_VERSION))

    print(f"parameter_space_run_id={run_id}")
    print(f"families={len(FAMILIES)}")
    print(f"parameter_candidates={len(selected)}")
    print(f"trial_limit={MAX_TRIALS}")
    print("oos_required=1")
    print("multiple_testing_required=1")
    print("live_allowed=0")
    print("VERDICT=STRATEGY_FAMILY_REGISTRY_V2_READY")


if __name__ == "__main__":
    main()
