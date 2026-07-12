CREATE OR REPLACE VIEW public.market_bars_ng_m5_rolling_v1 AS
WITH ranked AS (
    SELECT
        mb.*,
        row_number() OVER (
            PARTITION BY mb.ts
            ORDER BY coalesce(mb.volume, 0) DESC, mb.symbol
        ) AS liquidity_rank
    FROM public.market_bars mb
    WHERE mb.timeframe='M5'
      AND mb.symbol ~ '^NG[FGHJKMNQUVXZ][0-9]@RTSX$'
)
SELECT
    symbol, timeframe, ts, open, high, low, close,
    volume, created_at, source
FROM ranked
WHERE liquidity_rank=1;

COMMENT ON VIEW public.market_bars_ng_m5_rolling_v1 IS
'Natural Gas continuous M5 chain. For each timestamp selects the contract with the highest contemporaneous volume; no future data is used. Research only. V2.';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='finam') THEN
        GRANT SELECT ON public.market_bars_ng_m5_rolling_v1 TO finam;
    END IF;
END $$;
