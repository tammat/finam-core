INSERT INTO presentation.ui_resource_v1
(resource_key,locale_code,caption,caption_short,caption_mobile,tooltip,icon,resource_group) VALUES
('research.tile.methodology','ru','Методологическая проверка','Методика','Метод.','Количество кандидатов, проверенных единым методологическим контрактом','','research'),
('research.tile.method_pass','ru','Методологический PASS','Метод PASS','PASS','Кандидаты, прошедшие все шесть обязательных проверок','','research'),
('research.domain.methodology_gate','ru','Методология','Методика','Метод.','Шесть обязательных методологических проверок','','research')
ON CONFLICT(resource_key,locale_code) DO UPDATE SET
caption=EXCLUDED.caption,caption_short=EXCLUDED.caption_short,caption_mobile=EXCLUDED.caption_mobile,
tooltip=EXCLUDED.tooltip,icon=EXCLUDED.icon,resource_group=EXCLUDED.resource_group;
