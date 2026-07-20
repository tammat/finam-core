BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
('research.failures.column.not_evaluated','ru','Не проверялось','Не провер.','Не пров.','Варианты не дошли до этой проверки из-за отказа на предыдущем обязательном этапе','','research'),
('research.failures.column.detail','ru','Причина','Причина','Почему','Главная причина потери допуска на этапе','','research'),
('research.failures.gate.base','ru','Базовый OOS','Базовый OOS','OOS','Базовая walk-forward проверка до методологического контракта','','research'),
('research.failures.detail.base','ru','После издержек: {costs}; мало сделок: {sample}','Издержки: {costs}; выборка: {sample}','Изд. {costs}; выб. {sample}','Распределение отказов базового OOS','','research'),
('research.failures.detail.not_evaluated','ru','Предыдущий этап не пройден','Не проверялось','Не пров.','Эта проверка ещё не выполнялась','','research'),
('research.failures.detail.evaluated','ru','Отказов: {failed}; прошло: {passed}','Отказ: {failed}; PASS: {passed}','{failed}/{passed}','Итог среди вариантов, реально дошедших до проверки','','research'),
('research.domain.not_passed','ru','Не пройдено','Не пройдено','Отказ','Проверка выполнена, но обязательный критерий не достигнут','','research'),
('research.domain.not_passed.tooltip','ru','Обязательный критерий не достигнут','Не пройдено','Отказ','Это методологический отказ, а не техническая ошибка процесса','','research'),
('research.domain.not_evaluated','ru','Не проверялось','Не проверялось','Не пров.','Вариант не дошёл до этого этапа','','research'),
('research.domain.not_evaluated.tooltip','ru','Предыдущий обязательный этап не пройден','Не проверялось','Не пров.','Это не отказ и не техническая ошибка: проверка ещё не выполнялась','','research'),
('research.failures.column.not_evaluated','en','Not evaluated','Not eval.','N/A','Variants stopped at an earlier mandatory gate','','research'),
('research.failures.column.detail','en','Reason','Reason','Why','Primary admission loss reason','','research'),
('research.failures.gate.base','en','Base OOS','Base OOS','OOS','Base walk-forward gate before the methodology contract','','research'),
('research.failures.detail.base','en','After costs: {costs}; low sample: {sample}','Costs: {costs}; sample: {sample}','Cost {costs}; N {sample}','Base OOS rejection breakdown','','research'),
('research.failures.detail.not_evaluated','en','Previous gate not passed','Not evaluated','N/A','This gate has not run yet','','research'),
('research.failures.detail.evaluated','en','Failed: {failed}; passed: {passed}','Fail: {failed}; pass: {passed}','{failed}/{passed}','Results among variants that reached this gate','','research'),
('research.domain.not_passed','en','Not passed','Not passed','Failed','The gate ran but its mandatory criterion was not met','','research'),
('research.domain.not_passed.tooltip','en','Mandatory criterion not met','Not passed','Failed','Methodology rejection, not a system error','','research')
,
('research.domain.not_evaluated','en','Not evaluated','Not evaluated','N/A','The variant did not reach this gate','','research'),
('research.domain.not_evaluated.tooltip','en','Previous mandatory gate not passed','Not evaluated','N/A','This is neither a rejection nor a system error: the gate has not run','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,
 caption_mobile=excluded.caption_mobile,tooltip=excluded.tooltip,
 icon=excluded.icon,resource_group=excluded.resource_group;

COMMIT;
