BEGIN;
CREATE TABLE IF NOT EXISTS analytics.market_session_research_contract_v1(
 session_code text PRIMARY KEY,timezone_code text NOT NULL,local_start time NOT NULL,
 local_end time NOT NULL,weekdays jsonb NOT NULL,priority integer NOT NULL,
 enabled boolean NOT NULL DEFAULT true,description_ru text NOT NULL,
 CHECK(local_end>local_start));
INSERT INTO analytics.market_session_research_contract_v1 VALUES
 ('MOSCOW_OPEN','Europe/Moscow','09:50','10:45','[1,2,3,4,5]',100,true,'Открытие основной сессии Москвы'),
 ('EUROPE_OPEN','Europe/Berlin','08:50','10:30','[1,2,3,4,5]',90,true,'Открытие европейских площадок'),
 ('US_OPEN','America/New_York','09:20','10:30','[1,2,3,4,5]',95,true,'Открытие американского рынка'),
 ('EUROPE_US_OVERLAP','America/New_York','10:30','11:30','[1,2,3,4,5]',80,true,'Перекрытие Европы и США'),
 ('MOEX_MAIN','Europe/Moscow','10:45','18:30','[1,2,3,4,5]',50,true,'Основная московская сессия'),
 ('MOEX_EVENING','Europe/Moscow','19:00','23:50','[1,2,3,4,5]',40,true,'Вечерняя московская сессия'),
 ('MOEX_WEEKEND','Europe/Moscow','10:00','19:00','[7]',60,true,'Воскресная сессия при подтверждённом живом потоке')
ON CONFLICT(session_code) DO UPDATE SET timezone_code=EXCLUDED.timezone_code,
 local_start=EXCLUDED.local_start,local_end=EXCLUDED.local_end,weekdays=EXCLUDED.weekdays,
 priority=EXCLUDED.priority,enabled=true,description_ru=EXCLUDED.description_ru;
GRANT SELECT ON analytics.market_session_research_contract_v1 TO alex;
COMMIT;
