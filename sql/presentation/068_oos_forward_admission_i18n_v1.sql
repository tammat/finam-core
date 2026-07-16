INSERT INTO presentation.ui_resource_v1 (
    resource_key, locale_code, caption, caption_short, caption_mobile,
    tooltip, icon, resource_group
) VALUES
('status.forward_admission_decisions_complete','ru','Решения о допуске в форвардную когорту приняты','Решения приняты','Решения приняты','','','status'),
('status.duplicate_execution_fingerprint','ru','Дублирующий исполняемый сигнал исключён','Дубликат исключён','Дубликат','','','status'),
('status.forward_cohort_admission_pass','ru','Допущено в чистую форвардную когорту','Допущено','Допущено','','','status')
ON CONFLICT (resource_key, locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,
caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,
icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
