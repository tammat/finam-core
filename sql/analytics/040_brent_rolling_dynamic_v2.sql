CREATE OR REPLACE VIEW public.market_bars_br_m5_rolling_v2 AS
WITH legacy AS (
    SELECT mb.* FROM public.market_bars mb WHERE mb.timeframe='M5' AND (
        (mb.symbol='BRM5@RTSX' AND mb.ts<'2025-06-01 03:00:00+03') OR
        (mb.symbol='BRN5@RTSX' AND mb.ts>='2025-06-01 03:00:00+03' AND mb.ts<'2025-07-01 03:00:00+03') OR
        (mb.symbol='BRQ5@RTSX' AND mb.ts>='2025-07-01 03:00:00+03' AND mb.ts<'2025-08-01 03:00:00+03') OR
        (mb.symbol='BRU5@RTSX' AND mb.ts>='2025-08-01 03:00:00+03' AND mb.ts<'2025-09-01 03:00:00+03') OR
        (mb.symbol='BRV5@RTSX' AND mb.ts>='2025-09-01 03:00:00+03' AND mb.ts<'2025-10-01 03:00:00+03') OR
        (mb.symbol='BRX5@RTSX' AND mb.ts>='2025-10-01 03:00:00+03' AND mb.ts<'2025-11-01 03:00:00+03') OR
        (mb.symbol='BRZ5@RTSX' AND mb.ts>='2025-11-01 03:00:00+03' AND mb.ts<'2025-12-01 03:00:00+03') OR
        (mb.symbol='BRF6@RTSX' AND mb.ts>='2025-12-01 03:00:00+03' AND mb.ts<'2026-01-01 03:00:00+03') OR
        (mb.symbol='BRG6@RTSX' AND mb.ts>='2026-01-01 03:00:00+03' AND mb.ts<'2026-02-01 03:00:00+03') OR
        (mb.symbol='BRH6@RTSX' AND mb.ts>='2026-02-01 03:00:00+03' AND mb.ts<'2026-03-01 03:00:00+03') OR
        (mb.symbol='BRJ6@RTSX' AND mb.ts>='2026-03-01 03:00:00+03' AND mb.ts<'2026-04-01 03:00:00+03') OR
        (mb.symbol='BRK6@RTSX' AND mb.ts>='2026-04-01 03:00:00+03' AND mb.ts<'2026-05-01 03:00:00+03') OR
        (mb.symbol='BRM6@RTSX' AND mb.ts>='2026-05-01 03:00:00+03' AND mb.ts<'2026-06-01 03:00:00+03')
    )
), contract_windows AS (
    SELECT contract_symbol,expiration_date,
           lag(expiration_date) OVER(ORDER BY expiration_date) AS effective_from
    FROM public.futures_contract_universe
    WHERE root_symbol='BR' AND is_active AND expiration_date>='2026-06-01'
), current_chain AS (
    SELECT mb.* FROM public.market_bars mb JOIN contract_windows cw ON cw.contract_symbol=mb.symbol
    WHERE mb.timeframe='M5' AND mb.ts>=cw.effective_from::timestamp AND mb.ts<cw.expiration_date::timestamp
)
SELECT * FROM legacy UNION ALL SELECT * FROM current_chain;

COMMENT ON VIEW public.market_bars_br_m5_rolling_v2 IS
'Dynamic Brent continuous M5 chain. Historical fixed windows plus contract calendar from futures_contract_universe. V2.';
