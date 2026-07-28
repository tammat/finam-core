BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.oos.waiting.title','ru','Ожидают OOS','Ожидают','OOS','Варианты, которым нужны новые данные или дополнительная выборка до честной OOS-проверки.','','research'),
('research.oos.waiting.total','ru','Вариантов','Всего','Всего','Общее число вариантов, ожидающих OOS-проверку.','','research'),
('research.oos.waiting.reasons','ru','Причины','Причины','Причины','Распределение причин ожидания.','','research'),
('research.oos.waiting.reasons.value','ru','Издержки: {cost}; выборка: {sample}; новые данные: {future}','Издержки {cost} · выборка {sample} · данные {future}','{cost}/{sample}/{future}','Издержки — нужна более сильная ожидаемая доходность; выборка — мало сделок; новые данные — требуется future-only период.','','research'),
('research.oos.waiting.title','en','Awaiting OOS','Waiting','OOS','Variants that require new data or more evidence before honest OOS evaluation.','','research'),
('research.oos.waiting.total','en','Variants','Total','Total','Total variants awaiting OOS evaluation.','','research'),
('research.oos.waiting.reasons','en','Reasons','Reasons','Reasons','Waiting reason distribution.','','research'),
('research.oos.waiting.reasons.value','en','Costs: {cost}; sample: {sample}; new data: {future}','Costs {cost} · sample {sample} · data {future}','{cost}/{sample}/{future}','Costs need stronger expectancy; sample needs trades; new data needs a future-only period.','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
