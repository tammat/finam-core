INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('status.blocked','ru','Заблокировано','Блокировка','Блок.','','','status'),
('status.no_forward_cohort_candidates','ru','В текущей Forward-когорте нет кандидатов','Нет кандидатов','Нет','','','status'),
('status.no_eligible_forward_candidates','ru','Нет свежих допустимых Forward-кандидатов','Нет допустимых кандидатов','Нет','','','status'),
('status.awaiting_valid_forward_cohort','ru','Ожидается новая чистая Forward-когорта','Ожидается когорта','Ожидание','','','status'),
('status.forward_cohort_ready','ru','Forward-когорта готова','Когорта готова','Готово','','','status'),
('status.no_forward_cohort_candidates','en','Current Forward cohort has no candidates','No candidates','None','','','status'),
('status.no_eligible_forward_candidates','en','No fresh eligible Forward candidates','No eligible candidates','None','','','status'),
('status.awaiting_valid_forward_cohort','en','Awaiting a new clean Forward cohort','Awaiting cohort','Waiting','','','status'),
('status.forward_cohort_ready','en','Forward cohort is ready','Cohort ready','Ready','','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,
caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
