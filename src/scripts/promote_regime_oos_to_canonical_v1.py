from __future__ import annotations

import hashlib
import json
import uuid

import psycopg2
import psycopg2.extras


SOURCE_VERSION = "REGIME_OOS_CANONICAL_PROMOTION_V1"
VALIDATION_VERSION = "REGIME_COST_ADJUSTED_OOS_V2"
NAMESPACE = uuid.UUID("a405feaa-b0cd-5b76-88d5-ae7aceb2254f")


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                UPDATE analytics.edge_oos_result_v1 o
                SET verdict_code='OOS_FAIL',promotion_allowed=false,
                    reason='OOS_MARKET_DATA_STALE_AT_PROMOTION',updated_at=clock_timestamp()
                WHERE o.validation_version=%s AND o.promotion_allowed
                  AND NOT EXISTS (
                      SELECT 1 FROM public.market_bars b
                      WHERE b.symbol=o.symbol AND b.timeframe=o.timeframe
                        AND b.ts>=clock_timestamp()-interval '15 minutes'
                  )
            """, (VALIDATION_VERSION,))
            stale_revoked = cursor.rowcount
            cursor.execute("""
                WITH latest AS (
                    SELECT discovery_run_id
                    FROM analytics.edge_regime_hypothesis_result_v2
                    ORDER BY created_at DESC LIMIT 1
                )
                SELECT h.*,
                       (SELECT count(DISTINCT x.discovery_run_id)
                        FROM analytics.edge_regime_hypothesis_result_v2 x
                        WHERE x.strategy_code=h.strategy_code AND x.symbol=h.symbol
                          AND x.timeframe=h.timeframe AND x.parameter_json=h.parameter_json
                          AND x.regime_code=h.regime_code AND x.verdict_code='OOS_PASS') repeat_runs
                FROM analytics.edge_regime_hypothesis_result_v2 h
                JOIN LATERAL (
                    SELECT max(ts) latest_bar_ts FROM public.market_bars b
                    WHERE b.symbol=h.symbol AND b.timeframe=h.timeframe
                ) market ON true
                WHERE h.discovery_run_id=(SELECT discovery_run_id FROM latest)
                  AND h.verdict_code='OOS_PASS' AND h.trust_status='VERIFIED'
                  AND h.oos_trades>=30 AND h.oos_profit_factor>=1.20
                  AND h.oos_expectancy>0 AND h.folds_passed>=2
                  AND h.regime_coverage_ratio>=0.80 AND h.transaction_cost_bps>=8
                  AND h.parameter_json ? 'lookback' AND h.parameter_json ? 'hold'
                  AND market.latest_bar_ts>=clock_timestamp()-interval '15 minutes'
                ORDER BY h.hypothesis_score DESC,h.id LIMIT 1
            """)
            row = cursor.fetchone()
            if row is None:
                print(f"stale_canonical_promotions_revoked={stale_revoked}")
                print("canonical_candidates_promoted=0")
                print("VERDICT=REGIME_OOS_CANONICAL_PROMOTION_NO_PASS")
                return
            if int(row["repeat_runs"]) < 3:
                raise RuntimeError("REGIME_OOS_REPEATABILITY_NOT_PROVEN")

            params = dict(row["parameter_json"])
            params.update({
                "regime_code": row["regime_code"],
                "transaction_cost_bps": float(row["transaction_cost_bps"]),
            })
            canonical = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            parameter_hash = hashlib.sha256(canonical.encode()).hexdigest()
            identity = f"{row['strategy_code']}:{row['symbol']}:{row['timeframe']}:{parameter_hash}"
            observation_uuid = uuid.uuid5(NAMESPACE, "observation:" + identity)
            run_uuid = uuid.uuid5(NAMESPACE, "run:" + identity)
            candidate_uuid = uuid.uuid5(NAMESPACE, "candidate:" + identity)
            batch_id = f"REGIME_OOS_{row['discovery_run_id']}"

            cursor.execute(
                "SELECT count(*)::int,min(ts),max(ts) FROM public.market_bars WHERE symbol=%s AND timeframe=%s",
                (row["symbol"], row["timeframe"]),
            )
            bar_stats = cursor.fetchone()
            bars_total = int(bar_stats["count"])
            bars_start = bar_stats["min"]
            bars_end = bar_stats["max"]
            in_sample_bars = int(bars_total * 0.75)
            cursor.execute("""
                SELECT ts FROM public.market_bars
                WHERE symbol=%s AND timeframe=%s ORDER BY ts OFFSET %s LIMIT 1
            """, (row["symbol"], row["timeframe"], in_sample_bars))
            oos_start = cursor.fetchone()["ts"]

            cursor.execute("""
                INSERT INTO analytics.edge_observation_v1 (
                    observation_uuid,run_uuid,research_batch_id,research_code,strategy_code,
                    strategy_version,symbol,timeframe,parameter_hash,parameter_json,dataset_version,
                    market_data_version,runner_version,score_formula_version,market_regime,bars_used,
                    trades,profit_factor,expectancy,max_drawdown,stability_score,raw_edge_score,
                    normalized_edge_score,confidence_score,commission,slippage,verdict_code,source_version
                ) VALUES (%s,%s,%s,'REGIME_AWARE_EDGE_DISCOVERY_V2',%s,'v2',%s,%s,%s,%s,
                          %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,'OOS_PASS',%s)
                ON CONFLICT (run_uuid) DO UPDATE SET
                    parameter_json=EXCLUDED.parameter_json,verdict_code='OOS_PASS',updated_at=clock_timestamp()
            """, (
                str(observation_uuid),str(run_uuid),batch_id,row["strategy_code"],row["symbol"],
                row["timeframe"],parameter_hash,psycopg2.extras.Json(params),
                f"market_bars:{bars_start}:{bars_end}","analytics_regime_snapshots_v2",
                row["source_version"],VALIDATION_VERSION,row["regime_code"],bars_total,
                row["oos_trades"],row["oos_profit_factor"],row["oos_expectancy"],
                row["oos_max_drawdown"],row["folds_passed"] / row["folds_total"],
                row["hypothesis_score"],row["hypothesis_score"],row["regime_coverage_ratio"],SOURCE_VERSION,
            ))
            cursor.execute("""
                INSERT INTO analytics.edge_candidate_v1 (
                    candidate_uuid,observation_uuid,research_batch_id,research_code,strategy_code,
                    strategy_version,symbol,timeframe,parameter_hash,parameter_json,dataset_version,
                    raw_edge_score,normalized_edge_score,confidence_score,stability_score,
                    candidate_status,validation_stage,paper_allowed,shadow_allowed,micro_live_allowed,
                    live_allowed,source_version,discovery_batch_id,discovery_rank,discovery_score,
                    candidate_class,discovery_formula_version,validation_score,validation_reason,
                    validation_formula_version
                ) VALUES (%s,%s,%s,'REGIME_AWARE_EDGE_DISCOVERY_V2',%s,'v2',%s,%s,%s,%s,%s,
                          %s,%s,%s,%s,'OOS_PASS','OOS_COMPLETE',false,false,false,false,%s,%s,1,%s,
                          'REGIME_EDGE',%s,%s,'REGIME_COST_ADJUSTED_OOS_PASS',%s)
                ON CONFLICT (observation_uuid) DO UPDATE SET
                    candidate_status='OOS_PASS',validation_stage='OOS_COMPLETE',
                    validation_reason='REGIME_COST_ADJUSTED_OOS_PASS',updated_at=clock_timestamp()
            """, (
                str(candidate_uuid),str(observation_uuid),batch_id,row["strategy_code"],row["symbol"],
                row["timeframe"],parameter_hash,psycopg2.extras.Json(params),
                f"market_bars:{bars_start}:{bars_end}",row["hypothesis_score"],row["hypothesis_score"],
                row["regime_coverage_ratio"],row["folds_passed"] / row["folds_total"],SOURCE_VERSION,
                str(row["discovery_run_id"]),row["hypothesis_score"],row["source_version"],
                row["hypothesis_score"],VALIDATION_VERSION,
            ))
            cursor.execute("""
                INSERT INTO analytics.edge_oos_result_v1 (
                    observation_uuid,research_batch_id,strategy_code,symbol,timeframe,parameter_hash,
                    parameter_json,validation_version,in_sample_bars,oos_bars,oos_start,oos_end,
                    oos_trades,oos_profit_factor,oos_expectancy,oos_max_drawdown,folds_total,
                    folds_passed,verdict_code,promotion_allowed,reason
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                          'OOS_PASS',true,'REGIME_COST_ADJUSTED_OOS_PASS')
                ON CONFLICT (observation_uuid,validation_version) DO UPDATE SET
                    verdict_code='OOS_PASS',promotion_allowed=true,reason='REGIME_COST_ADJUSTED_OOS_PASS',
                    updated_at=clock_timestamp()
            """, (
                str(observation_uuid),batch_id,row["strategy_code"],row["symbol"],row["timeframe"],
                parameter_hash,psycopg2.extras.Json(params),VALIDATION_VERSION,in_sample_bars,
                bars_total-in_sample_bars,oos_start,bars_end,row["oos_trades"],row["oos_profit_factor"],
                row["oos_expectancy"],row["oos_max_drawdown"],row["folds_total"],row["folds_passed"],
            ))
            cursor.execute(
                "UPDATE analytics.edge_regime_hypothesis_result_v2 SET promotion_allowed=true WHERE id=%s",
                (row["id"],),
            )
    print(f"candidate_uuid={candidate_uuid}")
    print(f"observation_uuid={observation_uuid}")
    print(f"repeat_runs={row['repeat_runs']}")
    print(f"stale_canonical_promotions_revoked={stale_revoked}")
    print("canonical_candidates_promoted=1")
    print("paper_allowed=0")
    print("runtime_allowed=0")
    print("live_allowed=0")
    print("VERDICT=REGIME_OOS_CANONICAL_PROMOTION_V1_READY")


if __name__ == "__main__":
    main()
