INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.failures.title','ru','Причины отказа','Причины FAIL','FAIL','Разложение отказов последней методологической когорты по обязательным проверкам','','research'),
('research.failures.column.gate','ru','Проверка','Проверка','Gate','Обязательная методологическая проверка','','research'),
('research.failures.column.failed','ru','FAIL','FAIL','FAIL','Количество кандидатов, не прошедших проверку','','research'),
('research.failures.column.passed','ru','PASS','PASS','PASS','Количество кандидатов, прошедших проверку','','research'),
('research.failures.column.fail_pct','ru','Отказы, %','FAIL, %','%','Доля отказов в последней методологической когорте','','research'),
('research.failures.column.status','ru','Статус','Статус','Стат.','Итоговый статус проверки','','research'),
('research.failures.gate.statistical','ru','Статистика','Статистика','Стат.','Статистическая значимость с контролем множественных проверок FDR','','research'),
('research.failures.gate.robustness','ru','Устойчивость','Устойчивость','Устойч.','Устойчивость результата на соседних наборах параметров','','research'),
('research.failures.gate.holdout','ru','Holdout','Holdout','Hold.','Независимая финальная выборка, ранее не использованная для отбора','','research'),
('research.failures.gate.execution','ru','Исполнение','Исполнение','Исп.','Спред, задержка, влияние на рынок и частичное исполнение','','research'),
('research.failures.gate.capacity','ru','Ёмкость','Ёмкость','Ёмк.','Допустимый объём позиции с учётом ликвидности','','research'),
('research.failures.gate.portfolio','ru','Портфель','Портфель','Портф.','Дополнительный вклад и допустимая корреляция с портфелем','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
