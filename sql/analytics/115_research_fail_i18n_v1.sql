BEGIN;
INSERT INTO presentation.ui_resource_v1(
 resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,resource_group,source_version
) VALUES
 ('research.domain.fail','ru','Ошибка','Ошибка','Сбой','Процесс завершился с ошибкой','research','RESEARCH_FAIL_I18N_V1'),
 ('research.domain.fail.tooltip','ru','Процесс завершился с ошибкой','Ошибка процесса','Сбой','Процесс завершился с ошибкой; подробности доступны в строке анализа','research','RESEARCH_FAIL_I18N_V1')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
 caption=excluded.caption,caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,source_version=excluded.source_version,updated_at=now();
COMMIT;
