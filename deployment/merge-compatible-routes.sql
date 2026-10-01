\set ON_ERROR_STOP on
BEGIN;
UPDATE channels SET type=58, settings=(coalesce(nullif(settings,''),'{}')::jsonb || '{"advanced_custom":{"advanced_routes":[{"incoming_path":"/v1/messages","upstream_path":"/v1/anthropic/v1/messages","converter":"none","models":["claude-sonnet","claude-opus"]},{"incoming_path":"/v1/chat/completions","upstream_path":"/v1/chat/completions","converter":"none"},{"incoming_path":"/v1/responses","upstream_path":"/v1/openai/responses","converter":"none"},{"incoming_path":"/v1/messages","upstream_path":"/v1/chat/completions","converter":"anthropic_messages_to_openai_chat_completions"},{"incoming_path":"/v1beta/models/{model}:generateContent","upstream_path":"/v1/chat/completions","converter":"gemini_generate_content_to_openai_chat_completions"},{"incoming_path":"/v1/models","upstream_path":"/v1/models","converter":"none"}]}}'::jsonb)::text
WHERE name ILIKE 'merge%';
COMMIT;
