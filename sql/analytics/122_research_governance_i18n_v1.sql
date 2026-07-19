BEGIN;
INSERT INTO presentation.ui_resource_v1
 (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
 ('research.governance.title','ru','Контроль метода','Метод','Метод','Защита от переобучения, повторного holdout и ошибок денежных единиц.','','research'),
 ('research.tile.global_trials','ru','Все испытания','Испытания','Опыты','Накопительное число всех проверенных вариантов во всех циклах.','','research'),
 ('research.tile.global_pass','ru','Значимые','Значимые','PASS','Прошли поправку на общее число испытаний, а не только текущий цикл.','','research'),
 ('research.tile.holdout','ru','Чистый holdout','Holdout','Holdout','Независимые непересекающиеся финальные выборки; повторное чтение блокирует PASS.','','research'),
 ('research.tile.pnl_units','ru','P&L проверен','P&L','P&L','Проверены лот, шаг цены, стоимость шага, множитель и маржа.','','research'),
 ('research.tile.equities','ru','Акции','Акции','Акции','Число испытаний по акциям в последнем цикле.','','research'),
 ('research.tile.futures','ru','Фьючерсы','Фьючерсы','Фьюч.','Число испытаний по фьючерсам в последнем цикле.','','research'),
 ('research.tile.portfolio','ru','В портфель','Портфель','Портф.','Независимые кандидаты, прошедшие все ворота и портфельный отбор.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
 caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
 resource_group=EXCLUDED.resource_group;
COMMIT;
