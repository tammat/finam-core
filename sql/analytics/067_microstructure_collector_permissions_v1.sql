DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='finam') THEN
        GRANT USAGE ON SCHEMA analytics TO finam;
        GRANT SELECT ON analytics.forward_edge_shadow_trade_v1 TO finam;
        GRANT SELECT, INSERT ON analytics.market_microstructure_snapshot_v1 TO finam;
        GRANT SELECT, INSERT ON analytics.market_trade_tape_v1 TO finam;
        GRANT USAGE, SELECT ON SEQUENCE analytics.market_microstructure_snapshot_v1_snapshot_id_seq TO finam;
        GRANT SELECT ON public.market_data_watch_universe, public.signal_fills TO finam;
    END IF;
END $$;
