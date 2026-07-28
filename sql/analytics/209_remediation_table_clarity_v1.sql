BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.remediation.column.sources','ru','Исходных отказов','Отказов','Отказы','Число разных причин отказа, на основании которых создана ветка','','research'),
('research.remediation.column.created','ru','Создано вариантов','Вариантов','Создано','Все варианты, созданные этой веткой до проверок и отсева','','research'),
('research.remediation.column.pruned','ru','Исключено','Исключено','Отсев','Дубликаты и варианты, остановленные до OOS','','research'),
('research.remediation.column.queued','ru','Ожидают проверки','Ожидают','Ждут','Варианты, которым нужны данные или место в очереди','','research'),
('research.remediation.column.evaluated','ru','Проверено OOS','Проверено','OOS','Варианты с завершённой вневыборочной проверкой','','research'),
('research.remediation.column.result','ru','Результат проверки','Результат','Итог','До издержек → после издержек; сколько потеряно на издержках; итоговый OOS PASS','','research'),
('research.remediation.column.sources','en','Source failures','Failures','Fails','Distinct failure reasons used to create this branch','','research'),
('research.remediation.column.created','en','Variants created','Created','Created','All variants created before checks and pruning','','research'),
('research.remediation.column.pruned','en','Excluded','Excluded','Pruned','Duplicates and variants stopped before OOS','','research'),
('research.remediation.column.queued','en','Awaiting check','Awaiting','Waiting','Variants waiting for data or queue capacity','','research'),
('research.remediation.column.evaluated','en','OOS evaluated','Evaluated','OOS','Variants with a completed out-of-sample evaluation','','research'),
('research.remediation.column.result','en','Evaluation result','Result','Result','Before costs → after costs; cost losses; final OOS PASS','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=excluded.caption,caption_short=excluded.caption_short,
caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
