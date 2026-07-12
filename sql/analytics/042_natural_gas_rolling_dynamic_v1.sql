CREATE OR REPLACE VIEW public.market_bars_ng_m5_rolling_v1 AS
WITH legacy AS (
    SELECT mb.* FROM public.market_bars mb WHERE mb.timeframe='M5' AND (
        (mb.symbol='NGF6@RTSX' AND mb.ts<'2026-02-01 03:00:00+03') OR
        (mb.symbol='NGG6@RTSX' AND mb.ts>='2026-02-01 03:00:00+03' AND mb.ts<'2026-03-01 03:00:00+03') OR
        (mb.symbol='NGH6@RTSX' AND mb.ts>='2026-03-01 03:00:00+03' AND mb.ts<'2026-04-01 03:00:00+03') OR
        (mb.symbol='NGJ6@RTSX' AND mb.ts>='2026-04-01 03:00:00+03' AND mb.ts<'2026-05-01 03:00:00+03')
    )
), contract_windows AS (
    SELECT contract_symbol,expiration_date,lag(expiration_date) OVER(ORDER BY expiration_date) AS effective_from
    FROM public.futures_contract_universe WHERE root_symbol='NG' AND is_active AND status<>'QUARANTINE'
), current_chain AS (
    SELECT mb.* FROM public.market_bars mb JOIN contract_windows cw ON cw.contract_symbol=mb.symbol
    WHERE mb.timeframe='M5' AND cw.effective_from IS NOT NULL
      AND mb.ts>=cw.effective_from::timestamp AND mb.ts<cw.expiration_date::timestamp
)
SELECT * FROM legacy UNION ALL SELECT * FROM current_chain;

COMMENT ON VIEW public.market_bars_ng_m5_rolling_v1 IS
'Dynamic Natural Gas continuous M5 chain from contract calendar. Research only. V1.';
