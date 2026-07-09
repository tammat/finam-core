INSERT INTO presentation.ui_resource_v1
(resource_key, locale_code, caption, caption_short, caption_mobile, tooltip, icon, resource_group)
VALUES
('portfolio.source.presentation_v_workspace_v2_portfolio_positions_ru','ru','Позиции портфеля','Позиции','Поз.','Источник: workspace_v2 portfolio positions','', 'workspace_v2_portfolio'),
('portfolio.column.p&l %','ru','P&L %','P&L %','P&L %','Финансовый результат позиции в процентах','', 'workspace_v2_portfolio')
ON CONFLICT(resource_key, locale_code)
DO UPDATE SET
  caption=EXCLUDED.caption,
  caption_short=EXCLUDED.caption_short,
  caption_mobile=EXCLUDED.caption_mobile,
  tooltip=EXCLUDED.tooltip,
  icon=EXCLUDED.icon,
  resource_group=EXCLUDED.resource_group;
