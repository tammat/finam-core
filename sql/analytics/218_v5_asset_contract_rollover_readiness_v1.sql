BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_asset_contract_readiness_v1(
    asset_code text PRIMARY KEY CHECK(asset_code IN ('USD','GOLD','CNY')),
    runtime_symbol text UNIQUE NOT NULL,
    next_symbol text,
    rollover_mode text NOT NULL CHECK(rollover_mode IN ('CONTINUOUS','DATED_CONTRACT')),
    readiness_code text NOT NULL,
    research_entry_allowed boolean NOT NULL DEFAULT false,
    oos_allowed boolean NOT NULL DEFAULT false,
    reason text NOT NULL,
    source_identity text NOT NULL,
    source_as_of timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.v5_asset_contract_readiness_v1(
 asset_code,runtime_symbol,next_symbol,rollover_mode,readiness_code,
 research_entry_allowed,oos_allowed,reason,source_identity,source_as_of
) VALUES
 ('USD','USDRUBF@RTSX',NULL,'CONTINUOUS','CONTINUOUS_RESEARCH_READY',true,false,
  'MOEX perpetual contract with automatic daily extension; SwapRate funding is mandatory for net edge',
  'marketcore.instrument_reference_v1',(SELECT updated_at FROM marketcore.instrument_reference_v1 WHERE symbol='USDRUBF@RTSX')),
 ('CNY','CNYRUBF@RTSX',NULL,'CONTINUOUS','CONTINUOUS_RESEARCH_READY',true,false,
  'MOEX perpetual contract with automatic daily extension; SwapRate funding is mandatory for net edge',
  'marketcore.instrument_reference_v1',(SELECT updated_at FROM marketcore.instrument_reference_v1 WHERE symbol='CNYRUBF@RTSX')),
 ('GOLD','GDU6@RTSX','GDZ6@RTSX','DATED_CONTRACT','CURRENT_AND_NEXT_VISIBLE',true,false,
  'GDU6 Sep-2026 and GDZ6 Dec-2026 are tradable; rollover calendar must be completed before OOS',
  'marketcore.instrument_reference_v1',(SELECT max(updated_at) FROM marketcore.instrument_reference_v1 WHERE symbol IN ('GDU6@RTSX','GDZ6@RTSX')))
ON CONFLICT(asset_code) DO UPDATE SET runtime_symbol=excluded.runtime_symbol,
 next_symbol=excluded.next_symbol,rollover_mode=excluded.rollover_mode,
 readiness_code=excluded.readiness_code,research_entry_allowed=excluded.research_entry_allowed,
 oos_allowed=excluded.oos_allowed,reason=excluded.reason,
 source_identity=excluded.source_identity,source_as_of=excluded.source_as_of,
 updated_at=clock_timestamp();

CREATE OR REPLACE FUNCTION analytics.v5_asset_contract_entry_allowed_v1(p_symbol text)
RETURNS TABLE(allowed boolean,reason text,asset_code text)
LANGUAGE sql STABLE AS $$
 SELECT research_entry_allowed,readiness_code||':'||reason,asset_code
 FROM analytics.v5_asset_contract_readiness_v1 WHERE runtime_symbol=p_symbol
$$;

GRANT SELECT ON analytics.v5_asset_contract_readiness_v1 TO alex,finam;
GRANT EXECUTE ON FUNCTION analytics.v5_asset_contract_entry_allowed_v1(text) TO alex,finam;

COMMIT;
