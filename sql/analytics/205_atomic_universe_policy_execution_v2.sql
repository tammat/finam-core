BEGIN;

-- Служба runtime не получает прямых прав записи в таблицу политик.
-- Единственный разрешённый путь — проверенная атомарная функция.
ALTER FUNCTION analytics.activate_instrument_with_strategy_policy_v2(
    text,text,text,text,text,text,text,integer,double precision,text
) SECURITY DEFINER;

ALTER FUNCTION analytics.activate_instrument_with_strategy_policy_v2(
    text,text,text,text,text,text,text,integer,double precision,text
) SET search_path = pg_catalog, public, analytics;

REVOKE ALL ON analytics.runtime_strategy_policy_v2 FROM finam;
GRANT SELECT ON analytics.runtime_strategy_policy_v2 TO finam;
GRANT EXECUTE ON FUNCTION analytics.activate_instrument_with_strategy_policy_v2(
    text,text,text,text,text,text,text,integer,double precision,text
) TO finam;

COMMIT;
