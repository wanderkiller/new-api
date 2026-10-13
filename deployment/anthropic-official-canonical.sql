\set ON_ERROR_STOP on
-- Serve the canonical IDs on the Anthropic channel too: Vibe-Trading forwards
-- LANGCHAIN_REASONING_EFFORT only for names starting claude-opus-5 / claude-sonnet-5,
-- so the bare aliases would silently run at the model's default effort.
-- Prices: Anthropic list, identical to the existing alias expressions.
BEGIN;
UPDATE channels SET models='claude-sonnet,claude-opus,claude-sonnet-5-5,claude-opus-5-5' WHERE name='Anthropic Official' AND type=14;
INSERT INTO abilities ("group",model,channel_id,enabled,priority,weight,tag)
SELECT 'default',m,c.id,c.status=1,c.priority,c.weight,c.tag
FROM channels c CROSS JOIN unnest(ARRAY['claude-sonnet-5-5','claude-opus-5-5']) m
WHERE c.name='Anthropic Official'
ON CONFLICT ("group",model,channel_id) DO NOTHING;
INSERT INTO options(key,value) VALUES('billing_setting.billing_mode','{"claude-sonnet-5-5": "tiered_expr", "claude-opus-5-5": "tiered_expr"}') ON CONFLICT(key) DO UPDATE SET value=(options.value::jsonb || EXCLUDED.value::jsonb)::text;
INSERT INTO options(key,value) VALUES('billing_setting.billing_expr','{"claude-sonnet-5-5": "tier(\"standard\", p * 2 + c * 10 + cr * 0.2 + cc * 2.5 + cc1h * 4)", "claude-opus-5-5": "tier(\"standard\", p * 4 + c * 20 + cr * 0.2 + cc * 5 + cc1h * 8)"}') ON CONFLICT(key) DO UPDATE SET value=(options.value::jsonb || EXCLUDED.value::jsonb)::text;
COMMIT;
