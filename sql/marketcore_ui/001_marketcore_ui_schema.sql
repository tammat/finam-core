BEGIN;

CREATE SCHEMA IF NOT EXISTS marketcore_ui;

CREATE TABLE IF NOT EXISTS marketcore_ui.capital_summary_v1 (
    id SMALLINT PRIMARY KEY,
    planned_capital NUMERIC(20,2) NOT NULL,
    working_capital NUMERIC(20,2) NOT NULL,
    available_capital NUMERIC(20,2) NOT NULL,
    today_pnl NUMERIC(20,2) NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL,
    source_version TEXT NOT NULL,
    build_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS marketcore_ui.profit_summary_v1 (
    id SMALLINT PRIMARY KEY,
    production_edges INTEGER NOT NULL,
    paper_edges INTEGER NOT NULL,
    shadow_edges INTEGER NOT NULL,
    research_candidates INTEGER NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL,
    source_version TEXT NOT NULL,
    build_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS marketcore_ui.research_summary_v1 (
    id SMALLINT PRIMARY KEY,
    pipeline_status TEXT NOT NULL,
    top3_status TEXT NOT NULL,
    oos_pass INTEGER NOT NULL,
    paper_ready INTEGER NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL,
    source_version TEXT NOT NULL,
    build_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS marketcore_ui.risk_summary_v1 (
    id SMALLINT PRIMARY KEY,
    runtime_allowed BOOLEAN NOT NULL,
    execution_allowed BOOLEAN NOT NULL,
    micro_live_allowed BOOLEAN NOT NULL,
    daily_risk_pct NUMERIC(10,2) NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL,
    source_version TEXT NOT NULL,
    build_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS marketcore_ui.program_summary_v1 (
    id SMALLINT PRIMARY KEY,
    quarter TEXT NOT NULL,
    platform_status TEXT NOT NULL,
    research_status TEXT NOT NULL,
    top3_status TEXT NOT NULL,
    paper_status TEXT NOT NULL,
    marketcore_status TEXT NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL,
    source_version TEXT NOT NULL,
    build_id TEXT NOT NULL
);

COMMIT;
