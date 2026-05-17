create table if not exists moex_liquid_universe (
    symbol text primary key,
    asset_class text not null,
    board text,
    group_name text,
    enabled boolean not null default true,
    updated_at timestamptz not null default now()
);
