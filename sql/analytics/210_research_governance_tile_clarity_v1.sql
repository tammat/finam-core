BEGIN;

INSERT INTO presentation.ui_resource_v1
 (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
 ('research.tile.global_trials','ru','Проверено вариантов','Варианты','Варианты','Число зарегистрированных глобальных методологических испытаний. Это не количество сделок.','','research'),
 ('research.tile.global_pass','ru','Значимых PASS','PASS','PASS','Варианты, прошедшие статистическую значимость с поправкой на множественные испытания.','','research'),
 ('research.tile.holdout','ru','Чистых holdout','Holdout','Holdout','Независимые непересекающиеся финальные выборки.','','research'),
 ('research.tile.pnl_units','ru','P&L готово','P&L готово','P&L готово','Спецификации, где подтверждены лот, шаг цены, стоимость шага, множитель и маржа.','','research'),
 ('research.tile.pnl_blocks','ru','Ошибки P&L','Ошибки P&L','Ошибки','Спецификации с ошибкой денежных единиц или неполным контрактом; такие результаты заблокированы.','','research'),
 ('research.tile.equities','ru','PASS по акциям','Акции PASS','Акции','Методологические испытания по акциям в последнем цикле, допущенные к следующей стадии. Это не число акций или сделок.','','research'),
 ('research.tile.futures','ru','PASS по фьючерсам','Фьючерсы PASS','Фьючерсы','Методологические испытания по фьючерсам в последнем цикле, допущенные к следующей стадии. Это не число контрактов или сделок.','','research'),
 ('research.tile.portfolio','ru','Отобрано в портфель','В портфель','Портфель','Независимые кандидаты, прошедшие все ворота и портфельный отбор.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=EXCLUDED.caption,
 caption_short=EXCLUDED.caption_short,
 caption_mobile=EXCLUDED.caption_mobile,
 tooltip=EXCLUDED.tooltip,
 resource_group=EXCLUDED.resource_group;

COMMIT;
