BEGIN;
INSERT INTO presentation.ui_resource_v1
 (resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
 ('home.operator.diagnostic_funnels.title','ru','Диагностические воронки','Воронки','Воронки','Вход, выход, сессии, исполнение, риск и портфель.','','workspace_v2_home_operator'),
 ('home.operator.diagnostic_funnels.subtitle','ru','Где теряется edge','Шесть проверок','Проверки','Шесть независимых разложений потерь последнего цикла.','','workspace_v2_home_operator'),
 ('home.operator.diagnostic_funnels.summary','ru','Пройдено {passed} из {funnels} · максимум: {bottleneck}, −{lost}','{passed}/{funnels} · {bottleneck} −{lost}','{passed}/{funnels}','Главная потеря среди шести диагностических воронок.','','workspace_v2_home_operator')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=excluded.caption,
 caption_short=excluded.caption_short,caption_mobile=excluded.caption_mobile,
 tooltip=excluded.tooltip,resource_group=excluded.resource_group;
COMMIT;
