INSERT INTO public.futures_contract_universe (
    root_symbol,
    contract_symbol,
    asset_class,
    expiration_date,
    is_active,
    roll_priority,
    status
) VALUES
    ('GD', 'GDM6@RTSX', 'futures', NULL, false, 10, 'RESEARCH'),
    ('GD', 'GDU6@RTSX', 'futures', NULL, true, 20, 'RESEARCH'),
    ('GD', 'GDZ6@RTSX', 'futures', NULL, true, 30, 'RESEARCH')
ON CONFLICT (contract_symbol) DO UPDATE SET
    root_symbol=excluded.root_symbol,
    asset_class=excluded.asset_class,
    is_active=excluded.is_active,
    roll_priority=excluded.roll_priority,
    status=excluded.status,
    updated_at=now();
