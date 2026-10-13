\set ON_ERROR_STOP on
-- Anthropic first-party channel for the claude-sonnet / claude-opus aliases.
-- Inserted disabled with an empty key: paste the key in the web UI, then enable.
-- Priority 20 puts it ahead of the Merge channels (10, 8); Merge stays as retry fallback.
-- Pricing needs no change: billing_setting.billing_expr already bills both aliases at
-- Anthropic list price (sonnet-5-5 $2/$10, opus-5-5 $4/$20, cache read $0.20, 5m write 1.25x, 1h write 2x).
BEGIN;
INSERT INTO channels (type,key,status,name,weight,created_time,base_url,models,"group",model_mapping,priority,auto_ban,test_model,tag,setting,settings,channel_info)
SELECT 14,'',2,'Anthropic Official',0,extract(epoch FROM now())::bigint,'https://api.anthropic.com',
 'claude-sonnet,claude-opus','default',
 '{"claude-sonnet": "claude-sonnet-5-5", "claude-opus": "claude-opus-5-5"}',
 20,1,'claude-sonnet','',
 '{"force_format":false,"thinking_to_content":false,"proxy":"","pass_through_body_enabled":false,"system_prompt":"","system_prompt_override":false}',
 '{"allow_service_tier": false, "allow_inference_geo": false, "allow_safety_identifier": false, "allow_include_obfuscation": false}',
 '{"is_multi_key":false,"multi_key_size":0,"multi_key_status_list":null,"multi_key_polling_index":0,"multi_key_mode":""}'
WHERE NOT EXISTS (SELECT 1 FROM channels WHERE name='Anthropic Official');
INSERT INTO abilities ("group",model,channel_id,enabled,priority,weight,tag)
SELECT 'default',m,c.id,false,c.priority,c.weight,c.tag
FROM channels c CROSS JOIN unnest(ARRAY['claude-sonnet','claude-opus']) m
WHERE c.name='Anthropic Official'
ON CONFLICT ("group",model,channel_id) DO NOTHING;
COMMIT;
