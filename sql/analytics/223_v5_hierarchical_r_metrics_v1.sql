BEGIN;

ALTER TABLE analytics.hierarchical_evidence_v1
    ADD COLUMN IF NOT EXISTS net_pnl_r numeric,
    ADD COLUMN IF NOT EXISTS expectancy_r numeric,
    ADD COLUMN IF NOT EXISTS r_observable boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN analytics.hierarchical_evidence_v1.net_pnl_r IS
'Сумма net P&L, нормированная на первоначальный риск до entry stop для каждой сделки.';
COMMENT ON COLUMN analytics.hierarchical_evidence_v1.expectancy_r IS
'Средний net результат сделки в единицах первоначального риска R.';
COMMENT ON COLUMN analytics.hierarchical_evidence_v1.r_observable IS
'True только когда первоначальный stop и R доступны для всех сделок ветки.';

GRANT SELECT,INSERT,UPDATE ON analytics.hierarchical_evidence_v1 TO alex,finam;

COMMIT;
