BEGIN;

-- Keep the legacy table readable for old diagnostics, but make its dates follow
-- the canonical exchange calendar. New resolution code reads calendar/roll decisions.
UPDATE public.futures_contract_universe u
SET expiration_date=coalesce(c.last_trade_date,c.expiration_date),
    is_active=coalesce(c.last_trade_date,c.expiration_date)>=CURRENT_DATE,
    updated_at=clock_timestamp()
FROM public.futures_contract_calendar c
WHERE c.symbol=u.contract_symbol
  AND (u.expiration_date IS DISTINCT FROM coalesce(c.last_trade_date,c.expiration_date)
       OR u.is_active IS DISTINCT FROM (coalesce(c.last_trade_date,c.expiration_date)>=CURRENT_DATE));

COMMIT;
