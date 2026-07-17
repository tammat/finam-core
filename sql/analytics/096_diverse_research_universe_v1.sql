BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_research_universe_policy_v1 (
 policy_code text PRIMARY KEY,active boolean NOT NULL DEFAULT false,policy jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK(jsonb_typeof(policy)='object')
);
CREATE UNIQUE INDEX IF NOT EXISTS edge_research_universe_one_active_v1
 ON analytics.edge_research_universe_policy_v1(active) WHERE active;
INSERT INTO analytics.edge_research_universe_policy_v1(policy_code,active,policy) VALUES
('DIVERSE_RESEARCH_UNIVERSE_V1',true,'{
 "max_markets":12,
 "category_order":["OIL","GAS","METALS","FX","INDEX","EQUITY","OTHER"],
 "category_quotas":{"OIL":1,"GAS":1,"METALS":2,"FX":1,"INDEX":1,"EQUITY":5,"OTHER":1}
}'::jsonb) ON CONFLICT(policy_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS analytics.edge_research_universe_snapshot_v1 (
 snapshot_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 run_id uuid NOT NULL,stage_code text NOT NULL,policy_code text NOT NULL
 REFERENCES analytics.edge_research_universe_policy_v1(policy_code),
 symbol text NOT NULL,timeframe text NOT NULL,category_code text NOT NULL,bars bigint NOT NULL,
 latest_ts timestamptz NOT NULL,category_rank integer NOT NULL,overall_rank integer NOT NULL,
 selected boolean NOT NULL,reason_code text NOT NULL,contract_root text,expiration_date date,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),UNIQUE(run_id,stage_code,symbol)
);
CREATE INDEX IF NOT EXISTS edge_research_universe_latest_v1
 ON analytics.edge_research_universe_snapshot_v1(stage_code,created_at DESC);

CREATE OR REPLACE FUNCTION analytics.guard_research_universe_policy_v1()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF OLD.policy IS DISTINCT FROM NEW.policy THEN RAISE EXCEPTION 'RESEARCH_UNIVERSE_POLICY_IMMUTABLE'; END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS research_universe_policy_guard_v1 ON analytics.edge_research_universe_policy_v1;
CREATE TRIGGER research_universe_policy_guard_v1 BEFORE UPDATE ON analytics.edge_research_universe_policy_v1
FOR EACH ROW EXECUTE FUNCTION analytics.guard_research_universe_policy_v1();

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.universe.title','ru','Инструменты цикла','Инструменты','Рынки','Выбор инструментов последнего Walk-forward с причинами включения и исключения','','research'),
('research.universe.column.selected','ru','Выбор','Выбор','Выб.','Включён ли инструмент в цикл','','research'),
('research.universe.column.symbol','ru','Инструмент','Инструмент','Инстр.','Торговый символ','','research'),
('research.universe.column.category','ru','Категория','Категория','Кат.','Категория диверсификации','','research'),
('research.universe.column.bars','ru','Бары','Бары','Бары','Количество доступных M5-баров','','research'),
('research.universe.column.rank','ru','Место','Место','№','Место внутри категории','','research'),
('research.universe.column.reason','ru','Причина','Причина','Прич.','Причина включения или исключения','','research'),
('research.universe.category.oil','ru','Нефть','Нефть','Нефть','Фьючерсы на нефть','','research'),
('research.universe.category.gas','ru','Газ','Газ','Газ','Фьючерсы на природный газ','','research'),
('research.universe.category.metals','ru','Металлы','Металлы','Мет.','Драгоценные металлы','','research'),
('research.universe.category.fx','ru','Валюта','Валюта','FX','Валютные инструменты','','research'),
('research.universe.category.index','ru','Индексы','Индексы','Инд.','Рыночные индексы','','research'),
('research.universe.category.equity','ru','Акции','Акции','Акц.','Акции','','research'),
('research.universe.category.other','ru','Другие','Другие','Др.','Другие инструменты','','research'),
('research.universe.reason.category_quota_selected','ru','Квота','Квота','Кв.','Выбран по обязательной квоте категории','','research'),
('research.universe.reason.global_fill_selected','ru','Резерв','Резерв','Рез.','Выбран при заполнении оставшихся мест','','research'),
('research.universe.reason.category_quota_exceeded','ru','Вне квоты','Вне квоты','Нет','Не вошёл: квота категории исчерпана','','research'),
('research.domain.selected','ru','Выбран','Выбран','Да','Инструмент включён в цикл','','research'),
('research.domain.excluded','ru','Исключён','Исключён','Нет','Инструмент не включён в цикл','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;

COMMIT;
