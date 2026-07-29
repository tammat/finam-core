BEGIN;

INSERT INTO public.market_data_watch_universe (
    symbol,
    asset_group,
    timeframe,
    is_enabled,
    reason,
    updated_at
)
SELECT
    candidate.symbol,
    candidate.asset_group,
    'M1',
    true,
    'V5 rollover candidate prewarm',
    clock_timestamp()
FROM (
    VALUES
        ('BRU6@RTSX', 'BR'),
        ('NGU6@RTSX', 'GAS'),
        ('GDZ6@RTSX', 'GOLD')
) AS candidate(symbol, asset_group)
ON CONFLICT (symbol) DO UPDATE
SET
    is_enabled = true,
    asset_group = EXCLUDED.asset_group,
    reason = EXCLUDED.reason,
    updated_at = EXCLUDED.updated_at;

COMMIT;
