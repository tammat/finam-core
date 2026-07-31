CREATE TABLE IF NOT EXISTS analytics.market_event_risk_v1 (
 event_code text PRIMARY KEY,
 title_ru text NOT NULL,
 category_code text NOT NULL,
 risk_level text NOT NULL CHECK (risk_level IN ('NORMAL','ELEVATED','SHOCK','RECOVERY')),
 symbol_patterns text[] NOT NULL DEFAULT ARRAY['*']::text[],
 starts_at timestamptz NOT NULL,
 expires_at timestamptz,
 is_active boolean NOT NULL DEFAULT true,
 source_url text,
 source_note text,
 confirmed_by text NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.market_shock_gate_audit_v1 (
 id bigserial PRIMARY KEY,
 evaluated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 signal_id text,
 symbol text NOT NULL,
 side_code text,
 event_code text,
 risk_level text NOT NULL,
 state_code text NOT NULL,
 mode_code text NOT NULL,
 allowed boolean NOT NULL,
 reason_code text NOT NULL,
 completed_m15_bars integer NOT NULL DEFAULT 0,
 gap_atr numeric,
 spread_atr numeric,
 relative_volume numeric,
 market_context_fresh boolean NOT NULL DEFAULT false,
 evidence jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS market_shock_gate_audit_symbol_ts_v1
ON analytics.market_shock_gate_audit_v1(symbol,evaluated_at DESC);

DO $$ BEGIN
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='finam') THEN
  GRANT SELECT ON analytics.market_event_risk_v1 TO finam;
  GRANT SELECT,INSERT ON analytics.market_shock_gate_audit_v1 TO finam;
  GRANT USAGE,SELECT ON SEQUENCE analytics.market_shock_gate_audit_v1_id_seq TO finam;
 END IF;
 IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='alex') THEN
  GRANT SELECT,INSERT,UPDATE ON analytics.market_event_risk_v1 TO alex;
  GRANT SELECT ON analytics.market_shock_gate_audit_v1 TO alex;
 END IF;
END $$;
