BEGIN;

ALTER TABLE analytics.risk_control_decision_v2
    ADD COLUMN IF NOT EXISTS entry_price numeric,
    ADD COLUMN IF NOT EXISTS stop_price numeric,
    ADD COLUMN IF NOT EXISTS contract_multiplier numeric,
    ADD COLUMN IF NOT EXISTS projected_cluster_share numeric,
    ADD COLUMN IF NOT EXISTS degradation_status text;

COMMENT ON COLUMN analytics.risk_control_decision_v2.entry_price
    IS 'Цена входа, использованная риск-контуром';
COMMENT ON COLUMN analytics.risk_control_decision_v2.stop_price
    IS 'Цена защитного стопа, использованная риск-контуром';
COMMENT ON COLUMN analytics.risk_control_decision_v2.contract_multiplier
    IS 'Множитель контракта для расчёта риска';
COMMENT ON COLUMN analytics.risk_control_decision_v2.projected_cluster_share
    IS 'Доля коррелированного кластера после предполагаемого входа';
COMMENT ON COLUMN analytics.risk_control_decision_v2.degradation_status
    IS 'Состояние деградации стратегии на момент решения';

GRANT SELECT, INSERT ON analytics.risk_control_decision_v2 TO alex, finam;

COMMIT;
