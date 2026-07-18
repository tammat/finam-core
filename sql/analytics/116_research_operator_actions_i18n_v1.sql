BEGIN;
INSERT INTO presentation.ui_resource_v1(
 resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,resource_group,source_version
) VALUES
 ('research.universe.column.operator_action','ru','Действия','Действия','Действ.','Рекомендуемые действия оператора','research','RESEARCH_OPERATOR_ACTIONS_I18N_V1'),
 ('research.scout.column.operator_action','ru','Действия','Действия','Действ.','Рекомендуемые действия оператора','research','RESEARCH_OPERATOR_ACTIONS_I18N_V1'),
 ('research.operator_actions.open','ru','Открыть','Открыть','Открыть','Дважды нажмите, чтобы открыть рекомендуемые действия','research','RESEARCH_OPERATOR_ACTIONS_I18N_V1'),
 ('research.operator_actions.open.tooltip','ru','Двойной клик — действия','Двойной клик','2×','Дважды нажмите, чтобы открыть рекомендуемые действия','research','RESEARCH_OPERATOR_ACTIONS_I18N_V1')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,source_version=excluded.source_version,updated_at=now();
COMMIT;
