\set ON_ERROR_STOP on
BEGIN;
UPDATE channels
SET models = models || CASE WHEN models = '' THEN '' ELSE ',' END ||
    concat_ws(',', CASE WHEN NOT ('grok'=ANY(string_to_array(models,','))) THEN 'grok' END,
                   CASE WHEN NOT ('gpt-luna'=ANY(string_to_array(models,','))) THEN 'gpt-luna' END),
    model_mapping = ((COALESCE(NULLIF(model_mapping,''),'{}'))::jsonb || '{"grok":"xai/grok-4.7","gpt-luna":"openai/gpt-6-luna"}'::jsonb)::text
WHERE name ILIKE 'merge%'
AND NOT ('grok'=ANY(string_to_array(models,',')) AND 'gpt-luna'=ANY(string_to_array(models,',')));
INSERT INTO abilities ("group",model,channel_id,enabled,priority,weight,tag)
SELECT g, m, c.id, c.status=1, c.priority, c.weight, c.tag
FROM channels c CROSS JOIN unnest(string_to_array(c."group",',')) g
CROSS JOIN unnest(ARRAY['grok','gpt-luna']) m
WHERE c.name ILIKE 'merge%'
ON CONFLICT ("group",model,channel_id) DO UPDATE SET enabled=EXCLUDED.enabled,priority=EXCLUDED.priority,weight=EXCLUDED.weight,tag=EXCLUDED.tag;
INSERT INTO options (key,value) VALUES ('billing_setting.billing_mode','{"grok":"tiered_expr","gpt-luna":"tiered_expr"}')
ON CONFLICT (key) DO UPDATE SET value=(options.value::jsonb || EXCLUDED.value::jsonb)::text;
INSERT INTO options (key,value) VALUES ('billing_setting.billing_expr',
'{"grok":"len <= 200000 ? tier(\"standard\", p * 2 + c * 6 + cr * 0.5) : tier(\"long_context\", p * 2 + c * 12 + cr * 1)","gpt-luna":"len <= 272000 ? tier(\"standard\", p * 0.1 + c * 0.5 + cr * 0.01 + cc * 0.125) : tier(\"long_context\", p * 0.2 + c * 0.75 + cr * 0.02 + cc * 0.25)"}')
ON CONFLICT (key) DO UPDATE SET value=(options.value::jsonb || EXCLUDED.value::jsonb)::text;
COMMIT;
