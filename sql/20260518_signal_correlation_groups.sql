create table if not exists signal_correlation_groups (
    symbol text primary key,
    correlation_group text not null,
    updated_at timestamptz not null default now()
);

insert into signal_correlation_groups(symbol, correlation_group) values
('SBER@MISX','BANKS'),
('SBERP@MISX','BANKS'),
('VTBR@MISX','BANKS'),
('T@MISX','FINTECH'),

('GAZP@MISX','OIL_GAS'),
('LKOH@MISX','OIL_GAS'),
('ROSN@MISX','OIL_GAS'),
('NVTK@MISX','OIL_GAS'),
('SNGS@MISX','OIL_GAS'),
('SNGSP@MISX','OIL_GAS'),
('TATN@MISX','OIL_GAS'),
('TATNP@MISX','OIL_GAS'),

('PLZL@MISX','METALS'),
('GMKN@MISX','METALS'),
('CHMF@MISX','METALS'),
('MAGN@MISX','METALS'),
('NLMK@MISX','METALS'),
('ALRS@MISX','METALS'),

('MGNT@MISX','RETAIL'),
('X5@MISX','RETAIL'),
('OZON@MISX','RETAIL'),

('TRNFP@MISX','TRANSPORT'),
('FESH@MISX','TRANSPORT'),

('ASTR@MISX','TECH'),
('POSI@MISX','TECH')
on conflict(symbol) do update set
    correlation_group = excluded.correlation_group,
    updated_at = now();
