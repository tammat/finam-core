INSERT INTO presentation.ui_resource_v1(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('quality.reason.insufficient_bars','ru','Недостаточно баров','Мало баров','Бары','','','quality'),
('quality.reason.insufficient_trading_days','ru','Недостаточно торговых дней','Мало дней','Дни','','','quality'),
('quality.reason.stale_data','ru','История устарела','Устарело','Устарело','','','quality'),
('quality.reason.insufficient_regime_coverage','ru','Недостаточное покрытие режимами','Мало режимов','Режимы','','','quality'),
('status.ready','ru','Готово','Готово','Готово','','','status')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
