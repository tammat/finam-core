INSERT INTO public.market_data_watch_universe
    (symbol,asset_group,timeframe,is_enabled,reason,updated_at)
VALUES
    ('MXU6@RTSX','MX','M1',true,'IMOEX shadow execution proxy',now())
ON CONFLICT (symbol) DO UPDATE SET
    asset_group=excluded.asset_group,
    is_enabled=true,
    reason=excluded.reason,
    updated_at=now();

INSERT INTO public.futures_contract_universe
    (root_symbol,contract_symbol,asset_class,expiration_date,is_active,roll_priority,status,updated_at)
VALUES
    ('MX','MXU6@RTSX','futures','2026-09-17',true,10,'RESEARCH',now())
ON CONFLICT DO NOTHING;

INSERT INTO marketcore.instrument_reference_v1 (
    symbol,display_name,short_name,asset_class,exchange,board,currency,lot_size,
    min_price_step,price_scale,contract_size,expiration_date,is_active,is_tradable,
    first_seen,last_seen,updated_at,source,source_version,build_id
) VALUES (
    'MXU6@RTSX','MIX-9.26','MIX-9.26','FUTURE','MOEX','FUT','RUB',1,
    25,0,1,'2026-09-17',true,true,now(),now(),now(),
    'FINAM_ASSETS_API','MXU6_EXECUTION_PROXY_V1',gen_random_uuid()
)
ON CONFLICT (symbol) DO UPDATE SET
    display_name=excluded.display_name,short_name=excluded.short_name,
    asset_class=excluded.asset_class,exchange=excluded.exchange,board=excluded.board,
    currency=excluded.currency,lot_size=excluded.lot_size,min_price_step=excluded.min_price_step,
    price_scale=excluded.price_scale,contract_size=excluded.contract_size,
    expiration_date=excluded.expiration_date,is_active=true,is_tradable=true,
    last_seen=now(),updated_at=now(),source=excluded.source,
    source_version=excluded.source_version,build_id=excluded.build_id;
