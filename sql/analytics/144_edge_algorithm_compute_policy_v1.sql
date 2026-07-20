BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_algorithm_compute_policy_v1(
    algorithm_code text PRIMARY KEY REFERENCES analytics.edge_search_algorithm_registry_v1(algorithm_code),
    priority_rank integer NOT NULL CHECK(priority_rank > 0),
    policy_code text NOT NULL CHECK(policy_code IN ('FOCUS','SECONDARY','LIMITED','ANOMALY_REVIEW','DEPRIORITIZED')),
    coarse_budget integer NOT NULL CHECK(coarse_budget >= 0),
    full_oos_share numeric NOT NULL CHECK(full_oos_share BETWEEN 0 AND 1),
    promotion_blocked boolean NOT NULL DEFAULT false,
    research_policy jsonb NOT NULL DEFAULT '{}'::jsonb,
    reason_ru text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.edge_algorithm_compute_policy_v1
    (algorithm_code,priority_rank,policy_code,coarse_budget,full_oos_share,promotion_blocked,research_policy,reason_ru)
SELECT algorithm_code,100,'DEPRIORITIZED',4,.05,false,
       '{"early_stop":true}'::jsonb,
       'Убыточное семейство: минимальный вычислительный бюджет до появления новых оснований.'
FROM analytics.edge_search_algorithm_registry_v1
WHERE enabled
ON CONFLICT (algorithm_code) DO NOTHING;

INSERT INTO analytics.edge_algorithm_compute_policy_v1 VALUES
('DONCHIAN_VOL_BREAKOUT',1,'FOCUS',48,.10,false,
 '{"entry":"TREND_AND_VOLUME_CONFIRMATION","exit":"DYNAMIC_MAX_20","early_exit":["TREND_LOSS","RISK_EXPANSION"],"regimes":["TREND_UP","TREND_DOWN","COMPRESSION_BREAKOUT"]}',
 '3 из 5 фолдов: расширять вход, динамический выход и режимные фильтры.',clock_timestamp()),
('EMA_TREND',2,'SECONDARY',32,.08,false,
 '{"stratify_by":["SESSION","VOLATILITY"],"early_stop":true}',
 '2 из 5 фолдов: проверить торговые сессии и режимы волатильности.',clock_timestamp()),
('MOMENTUM',3,'LIMITED',12,.05,false,
 '{"limited_research":true,"early_stop":true}',
 '1 из 5 фолдов: только ограниченное исследование.',clock_timestamp()),
('RSI',90,'ANOMALY_REVIEW',0,0,true,
 '{"anomaly":"EXTREME_PF_WITH_ZERO_FOLDS","research_disabled_until_review":true}',
 'Аномальный PF при 0 из 5 фолдов: продвижение и вычислительное расширение запрещены до аудита.',clock_timestamp())
ON CONFLICT (algorithm_code) DO UPDATE SET
 priority_rank=excluded.priority_rank,policy_code=excluded.policy_code,
 coarse_budget=excluded.coarse_budget,full_oos_share=excluded.full_oos_share,
 promotion_blocked=excluded.promotion_blocked,research_policy=excluded.research_policy,
 reason_ru=excluded.reason_ru,updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.edge_algorithm_anomaly_review_v1(
    review_id uuid PRIMARY KEY,
    algorithm_code text NOT NULL REFERENCES analytics.edge_search_algorithm_registry_v1(algorithm_code),
    search_run_id uuid NOT NULL,
    observed_profit_factor numeric,
    folds_passed integer,
    anomaly_code text NOT NULL,
    status_code text NOT NULL DEFAULT 'PENDING' CHECK(status_code IN ('PENDING','CONFIRMED','CLEARED')),
    promotion_blocked boolean NOT NULL DEFAULT true,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    reviewed_at timestamptz,
    UNIQUE(algorithm_code,search_run_id,anomaly_code)
);

INSERT INTO analytics.edge_algorithm_anomaly_review_v1
 (review_id,algorithm_code,search_run_id,observed_profit_factor,folds_passed,anomaly_code,evidence)
SELECT md5(a.algorithm_code||':'||a.search_run_id::text||':EXTREME_PF_ZERO_FOLDS')::uuid,
       a.algorithm_code,a.search_run_id,(a.best_metrics->>'profit_factor')::numeric,
       (a.best_metrics->>'folds')::integer,
       'EXTREME_PF_ZERO_FOLDS',jsonb_build_object('verdict',a.verdict_code,'source','edge_search_algorithm_analysis_v1')
FROM analytics.edge_search_algorithm_analysis_v1 a
WHERE a.algorithm_code='RSI' AND (a.best_metrics->>'profit_factor')::numeric>=10
  AND (a.best_metrics->>'folds')::integer=0
ON CONFLICT DO NOTHING;

GRANT SELECT,INSERT,UPDATE ON analytics.edge_algorithm_compute_policy_v1 TO alex,finam;
GRANT SELECT,INSERT,UPDATE ON analytics.edge_algorithm_anomaly_review_v1 TO alex,finam;

COMMIT;
