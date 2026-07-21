BEGIN;

CREATE OR REPLACE VIEW analytics.strategy_walkforward_latest_v1 AS
SELECT DISTINCT ON (
    strategy, symbol, timeframe, regime, trade_source,
    train_from, train_to, test_from, test_to
) w.*
FROM public.strategy_walkforward_results w
ORDER BY
    strategy, symbol, timeframe, regime, trade_source,
    train_from, train_to, test_from, test_to,
    computed_at DESC, id DESC;

COMMIT;
