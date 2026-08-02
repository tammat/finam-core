BEGIN;

-- External events are admission gates only.  They never create LONG/SHORT.
INSERT INTO analytics.market_event_risk_v1(
    event_code,title_ru,category_code,risk_level,symbol_patterns,starts_at,expires_at,
    is_active,source_url,source_note,confirmed_by,updated_at
) VALUES
(
    'OPEC_PLUS_2026_08_02_AWAITING',
    'OPEC+: ожидается официальное решение от 2 августа',
    'ENERGY_POLICY','ELEVATED',
    ARRAY['BRQ6@RTSX','NGQ6@RTSX','CNYRUBF@RTSX','USDRUBF@RTSX','GLDRUBF@RTSX','GDU6@RTSX'],
    timestamptz '2026-08-02 18:00:00+03',timestamptz '2026-08-04 12:00:00+03',true,
    'https://www.opec.org/pr-detail/1835609-5-july-2026.html',
    'AWAITING_CONFIRMATION; replace with the official 2 August communiqué before changing direction or expiry',
    'codex_primary_source_review',clock_timestamp()
),
(
    'EIA_OIL_2026_08_05',
    'EIA: еженедельные запасы нефти',
    'ENERGY_INVENTORY','ELEVATED',ARRAY['BRQ6@RTSX'],
    timestamptz '2026-08-05 17:00:00+03',timestamptz '2026-08-05 18:15:00+03',true,
    'https://www.eia.gov/petroleum/supply/weekly/schedule.php',
    'Scheduled weekly release; gate only, never a directional signal',
    'codex_primary_source_review',clock_timestamp()
),
(
    'EIA_GAS_2026_08_06',
    'EIA: еженедельные запасы природного газа',
    'ENERGY_INVENTORY','ELEVATED',ARRAY['NGQ6@RTSX'],
    timestamptz '2026-08-06 17:00:00+03',timestamptz '2026-08-06 18:15:00+03',true,
    'https://ir.eia.gov/ngs/schedule.html',
    'Scheduled weekly release; gate only, never a directional signal',
    'codex_primary_source_review',clock_timestamp()
),
(
    'CHINA_CPI_2026_08_09',
    'Китай: CPI/PPI',
    'CHINA_MACRO','ELEVATED',
    ARRAY['CNYRUBF@RTSX','GLDRUBF@RTSX','GDU6@RTSX','BRQ6@RTSX','NGQ6@RTSX'],
    timestamptz '2026-08-09 04:00:00+03',timestamptz '2026-08-09 05:15:00+03',true,
    'https://www.stats.gov.cn/english/PressRelease/ReleaseCalendar/202512/t20251226_1962154.html',
    'Official NBS release calendar; Moscow time derived from 09:30 Beijing',
    'codex_primary_source_review',clock_timestamp()
),
(
    'CHINA_PMI_2026_08_31',
    'Китай: производственный PMI',
    'CHINA_MACRO','ELEVATED',
    ARRAY['CNYRUBF@RTSX','GLDRUBF@RTSX','GDU6@RTSX','BRQ6@RTSX','NGQ6@RTSX'],
    timestamptz '2026-08-31 04:00:00+03',timestamptz '2026-08-31 05:15:00+03',true,
    'https://www.stats.gov.cn/english/PressRelease/ReleaseCalendar/202512/t20251226_1962154.html',
    'Official NBS release calendar; Moscow time derived from 09:30 Beijing',
    'codex_primary_source_review',clock_timestamp()
),
(
    'CBR_RATE_2026_09_11',
    'Банк России: решение по ключевой ставке',
    'MONETARY_POLICY','ELEVATED',
    ARRAY['SBER@MISX','CNYRUBF@RTSX','USDRUBF@RTSX'],
    timestamptz '2026-09-11 13:00:00+03',timestamptz '2026-09-11 15:30:00+03',true,
    'https://www.cbr.ru/DKP/cal_mp/',
    'Press release expected at 13:30 MSK; press conference expected at 15:00 MSK',
    'codex_primary_source_review',clock_timestamp()
)
ON CONFLICT(event_code) DO UPDATE SET
    title_ru=excluded.title_ru,category_code=excluded.category_code,
    risk_level=excluded.risk_level,symbol_patterns=excluded.symbol_patterns,
    starts_at=excluded.starts_at,expires_at=excluded.expires_at,is_active=excluded.is_active,
    source_url=excluded.source_url,source_note=excluded.source_note,
    confirmed_by=excluded.confirmed_by,updated_at=clock_timestamp();

INSERT INTO public.market_event_calendar(
    event_time,event_type,instrument_group,event_name,severity,source,
    pre_event_block_min,pre_event_reduce_min,is_active,raw_json,root_symbol,impact,title,updated_at
) VALUES
('2026-08-05 17:30:00+03','EIA_INVENTORY','BR','EIA: запасы нефти','HIGH','EIA',30,90,true,
 '{"source_url":"https://www.eia.gov/petroleum/supply/weekly/schedule.php","directional_signal":false}'::jsonb,
 'BRQ6','VOLATILITY','Запасы нефти EIA',clock_timestamp()),
('2026-08-06 17:30:00+03','EIA_GAS_STORAGE','NG','EIA: запасы природного газа','HIGH','EIA',30,90,true,
 '{"source_url":"https://ir.eia.gov/ngs/schedule.html","directional_signal":false}'::jsonb,
 'NGQ6','VOLATILITY','Запасы газа EIA',clock_timestamp()),
('2026-08-09 04:30:00+03','CHINA_CPI','CNY','Китай: CPI/PPI','HIGH','NBS_CHINA',30,120,true,
 '{"source_url":"https://www.stats.gov.cn/english/PressRelease/ReleaseCalendar/202512/t20251226_1962154.html","directional_signal":false}'::jsonb,
 'CNYRUBF','MACRO_VOLATILITY','Китай CPI/PPI',clock_timestamp()),
('2026-08-31 04:30:00+03','CHINA_PMI','CNY','Китай: производственный PMI','HIGH','NBS_CHINA',30,120,true,
 '{"source_url":"https://www.stats.gov.cn/english/PressRelease/ReleaseCalendar/202512/t20251226_1962154.html","directional_signal":false}'::jsonb,
 'CNYRUBF','MACRO_VOLATILITY','Китай PMI',clock_timestamp()),
('2026-09-11 13:30:00+03','CBR_RATE_DECISION','RUB','Банк России: ключевая ставка','HIGH','CBR',120,1440,true,
 '{"source_url":"https://www.cbr.ru/DKP/cal_mp/","directional_signal":false}'::jsonb,
 'SBER','RATE_VOLATILITY','Решение Банка России',clock_timestamp())
ON CONFLICT(event_time,event_type,instrument_group,event_name) DO UPDATE SET
    severity=excluded.severity,source=excluded.source,
    pre_event_block_min=excluded.pre_event_block_min,
    pre_event_reduce_min=excluded.pre_event_reduce_min,is_active=true,
    raw_json=excluded.raw_json,root_symbol=excluded.root_symbol,
    impact=excluded.impact,title=excluded.title,updated_at=clock_timestamp();

COMMIT;
