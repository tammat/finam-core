BEGIN;
INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('home.operator.main_loss.title','ru','Главная потеря','Потеря','Потеря','Этап с максимальным сокращением числа вариантов.','','workspace_v2_home_operator'),
('home.operator.main_loss.subtitle','ru','Где исчезает edge','Где теряем','Потеря','Последний подтверждённый bottleneck исследовательской или сигнальной воронки.','','workspace_v2_home_operator'),
('home.operator.main_loss.summary','ru','{stage} · потеряно {lost}','{stage} · −{lost}','−{lost}','Этап и количество потерянных вариантов.','','workspace_v2_home_operator'),
('home.operator.loss_solution.title','ru','Решение','Решение','Решение','Системный метод устранения основной потери.','','workspace_v2_home_operator'),
('home.operator.loss_solution.subtitle','ru','Что изменит система','Следующий метод','Метод','Решение формируется из DB-контракта без ослабления PASS.','','workspace_v2_home_operator'),
('home.operator.loss_solution.summary','ru','{solution}','{solution}','{solution}','Рекомендуемое системное действие для следующего цикла.','','workspace_v2_home_operator')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,resource_group=EXCLUDED.resource_group;
COMMIT;
