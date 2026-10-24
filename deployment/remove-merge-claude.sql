\set ON_ERROR_STOP on
BEGIN;
UPDATE channels SET
  models=array_to_string(array_remove(array_remove(string_to_array(models,','),'claude-sonnet'),'claude-opus'),','),
  model_mapping=((model_mapping::jsonb) - 'claude-sonnet' - 'claude-opus')::text,
  settings=jsonb_set(settings::jsonb,'{advanced_custom,advanced_routes}',
    (SELECT COALESCE(jsonb_agg(r),'[]'::jsonb) FROM jsonb_array_elements(settings::jsonb->'advanced_custom'->'advanced_routes') r
     WHERE NOT COALESCE((r->'models') ?| ARRAY['claude-sonnet','claude-opus'],false)))::text
WHERE name ILIKE 'merge%';
DELETE FROM abilities WHERE channel_id IN (SELECT id FROM channels WHERE name ILIKE 'merge%') AND model IN ('claude-sonnet','claude-opus');
UPDATE options SET value=(SELECT jsonb_agg(r) FROM jsonb_array_elements(value::jsonb) r WHERE r->>'name'<>'merge claude failover')::text WHERE key='channel_affinity_setting.rules';
COMMIT;
