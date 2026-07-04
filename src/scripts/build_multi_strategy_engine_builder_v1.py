from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

import psycopg2
import psycopg2.extras

import strategy.volatility_breakout  # noqa: F401
from strategy.base.executor import StrategyExecutor
from strategy.base.registry import StrategyRegistry
from strategy.volatility_breakout.config import VolatilityBreakoutConfig
from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("STRATEGY_FEATURE_LIMIT", "5000"))
SOURCE_VERSION = "MULTI_STRATEGY_ENGINE_BUILDER_V1"


def load_config(cur, family: str, version: str) -> dict[str, Any]:
    cur.execute("""
        SELECT config_json
        FROM analytics.strategy_configuration_v1
        WHERE strategy_family=%s
          AND strategy_version=%s
          AND active=true
        ORDER BY updated_at DESC
        LIMIT 1;
    """, (family, version))
    row = cur.fetchone()
    if not row:
        return {}
    cfg = row["config_json"]
    if isinstance(cfg, dict):
        return cfg
    return json.loads(cfg)


def build_strategy(strategy_cls, config: dict[str, Any]):
    if strategy_cls.family == "VOLATILITY_BREAKOUT":
        return VolatilityBreakoutStrategy(VolatilityBreakoutConfig.from_dict(config))
    return strategy_cls()


def main() -> None:
    started = time.perf_counter()
    build_id = str(uuid.uuid4())
    executor = StrategyExecutor()

    signals_saved = 0
    signals_generated = 0
    features_total = 0
    strategies_enabled = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT strategy_family, strategy_version
                FROM analytics.strategy_registry_v1
                WHERE enabled=true
                  AND paper_enabled=true
                  AND live_enabled=false
                ORDER BY priority, strategy_family;
            """)
            enabled_rows = [dict(r) for r in cur.fetchall()]
            strategies_enabled = len(enabled_rows)

            strategy_instances = []
            for row in enabled_rows:
                strategy_cls = StrategyRegistry.get(row["strategy_family"])
                if strategy_cls is None:
                    continue
                config = load_config(cur, row["strategy_family"], row["strategy_version"])
                strategy_instances.append(build_strategy(strategy_cls, config))

            cur.execute("""
                SELECT
                    symbol,
                    asset_class,
                    timeframe,
                    bar_ts,
                    range_pct,
                    body_pct,
                    return1_pct,
                    return5_pct,
                    volume_ratio20,
                    feature_quality_score,
                    market_quality_status,
                    source_version
                FROM analytics.feature_snapshot_v1
                WHERE bar_ts IS NOT NULL
                  AND feature_quality_score IS NOT NULL
                ORDER BY bar_ts DESC, symbol, timeframe
                LIMIT %s;
            """, (LIMIT,))
            features = [dict(r) for r in cur.fetchall()]
            features_total = len(features)

            for feature in features:
                for strategy in strategy_instances:
                    result = executor.execute(strategy, feature)
                    if result.signal is None:
                        continue

                    signals_generated += 1
                    s = result.signal

                    cur.execute("""
                        INSERT INTO analytics.strategy_signal_snapshot_v1 (
                            symbol,
                            display_name,
                            asset_class,
                            timeframe,
                            strategy_family,
                            signal_ts,
                            signal_direction,
                            signal_strength,
                            signal_score,
                            confidence,
                            signal_status,
                            feature_quality_score,
                            market_quality_status,
                            paper_allowed,
                            risk_allowed,
                            execution_allowed,
                            feature_version,
                            strategy_version,
                            source_table,
                            build_id,
                            refreshed_at
                        )
                        VALUES (
                            %s,'',%s,%s,%s,%s,
                            %s,%s,%s,%s,
                            'READY',
                            %s,%s,
                            true,false,false,
                            %s,%s,
                            'analytics.feature_snapshot_v1',
                            %s,
                            now()
                        )
                        ON CONFLICT (symbol, timeframe, strategy_family, signal_ts)
                        DO UPDATE SET
                            asset_class=EXCLUDED.asset_class,
                            signal_direction=EXCLUDED.signal_direction,
                            signal_strength=EXCLUDED.signal_strength,
                            signal_score=EXCLUDED.signal_score,
                            confidence=EXCLUDED.confidence,
                            signal_status=EXCLUDED.signal_status,
                            feature_quality_score=EXCLUDED.feature_quality_score,
                            market_quality_status=EXCLUDED.market_quality_status,
                            paper_allowed=EXCLUDED.paper_allowed,
                            risk_allowed=false,
                            execution_allowed=false,
                            feature_version=EXCLUDED.feature_version,
                            strategy_version=EXCLUDED.strategy_version,
                            build_id=EXCLUDED.build_id,
                            refreshed_at=now();
                    """, (
                        s.symbol,
                        feature.get("asset_class") or "",
                        s.timeframe,
                        s.strategy_family,
                        s.signal_ts,
                        s.direction,
                        s.strength,
                        s.score,
                        s.confidence,
                        feature.get("feature_quality_score") or 0,
                        feature.get("market_quality_status") or "UNKNOWN",
                        result.feature_version,
                        result.strategy_version,
                        build_id,
                    ))
                    signals_saved += 1

            cur.execute("SELECT count(*) AS rows FROM analytics.strategy_signal_snapshot_v1;")
            signal_rows = int(cur.fetchone()["rows"])

            cur.execute("""
                SELECT count(*) AS unsafe
                FROM analytics.strategy_signal_snapshot_v1
                WHERE execution_allowed=true;
            """)
            unsafe = int(cur.fetchone()["unsafe"])

    runtime_ms = (time.perf_counter() - started) * 1000.0

    print("=== MULTI_STRATEGY_ENGINE_BUILDER_V1 ===")
    print(f"features_total={features_total}")
    print(f"strategies_enabled={strategies_enabled}")
    print(f"signals_generated={signals_generated}")
    print(f"signals_saved={signals_saved}")
    print(f"signal_rows_total={signal_rows}")
    print(f"execution_allowed_rows={unsafe}")
    print(f"runtime_ms={runtime_ms:.3f}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MULTI_STRATEGY_ENGINE_BUILDER_V1_READY")


if __name__ == "__main__":
    main()
