BEGIN;

CREATE TABLE IF NOT EXISTS analytics.session_gap_entry_policy_v1 (
    policy_id bigserial PRIMARY KEY,
    policy_code text NOT NULL UNIQUE,
    symbol_pattern text NOT NULL,
    timeframe text NOT NULL,
    atr_lookback integer NOT NULL CHECK (atr_lookback >= 5),
    elevated_gap_atr numeric NOT NULL CHECK (elevated_gap_atr > 0),
    extreme_gap_atr numeric NOT NULL CHECK (extreme_gap_atr > elevated_gap_atr),
    confirmation_bars integer NOT NULL CHECK (confirmation_bars >= 1),
    priority integer NOT NULL DEFAULT 0,
    active boolean NOT NULL DEFAULT true,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.session_gap_entry_decision_v1 (
    decision_id bigserial PRIMARY KEY,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    bar_ts timestamptz NOT NULL,
    previous_close numeric,
    bar_open numeric NOT NULL,
    prior_atr numeric,
    gap_atr_ratio numeric,
    decision_code text NOT NULL,
    reason_code text NOT NULL,
    confirmation_remaining integer NOT NULL DEFAULT 0,
    decided_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(symbol,timeframe,bar_ts)
);

INSERT INTO analytics.session_gap_entry_policy_v1(
    policy_code,symbol_pattern,timeframe,atr_lookback,elevated_gap_atr,
    extreme_gap_atr,confirmation_bars,priority
) VALUES
    ('GENERIC_M1','%','M1',20,1.5,3.0,3,10),
    ('GENERIC_M5','%','M5',20,1.5,3.0,3,10),
    ('GENERIC_M15','%','M15',20,1.5,3.0,3,10),
    ('GENERIC_H1','%','H1',20,1.5,3.0,2,10)
ON CONFLICT(policy_code) DO UPDATE SET
    symbol_pattern=excluded.symbol_pattern,
    timeframe=excluded.timeframe,
    atr_lookback=excluded.atr_lookback,
    elevated_gap_atr=excluded.elevated_gap_atr,
    extreme_gap_atr=excluded.extreme_gap_atr,
    confirmation_bars=excluded.confirmation_bars,
    priority=excluded.priority,
    active=true,
    updated_at=now();

GRANT SELECT ON analytics.session_gap_entry_policy_v1 TO alex,finam;
GRANT SELECT,INSERT,UPDATE ON analytics.session_gap_entry_decision_v1 TO alex,finam;
GRANT USAGE,SELECT ON SEQUENCE analytics.session_gap_entry_decision_v1_decision_id_seq TO alex,finam;

COMMIT;
