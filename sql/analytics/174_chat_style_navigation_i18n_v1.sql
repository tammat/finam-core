BEGIN;

INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group)
VALUES
  ('workspace.drawer.brand','ru','MarketCore','MarketCore','MarketCore','Главное меню MarketCore','','workspace'),
  ('workspace.drawer.views','ru','Представление','Вид','Вид','Выбор объёма отображаемых данных','','workspace'),
  ('workspace.drawer.sections','ru','Разделы','Разделы','Разделы','Переход к разделам текущей страницы','','workspace')
ON CONFLICT(resource_key,locale_code) DO UPDATE
SET caption=excluded.caption,
    caption_short=excluded.caption_short,
    caption_mobile=excluded.caption_mobile,
    tooltip=excluded.tooltip,
    icon=excluded.icon,
    resource_group=excluded.resource_group;

COMMIT;
