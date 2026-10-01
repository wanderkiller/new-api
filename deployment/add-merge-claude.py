import json,subprocess
from pathlib import Path
q="SELECT coalesce(json_agg(t),'[]') FROM (SELECT id,name,type,models,model_mapping,settings FROM channels WHERE name ILIKE 'merge%' ORDER BY id) t"
channels=json.loads(subprocess.check_output(['sudo','-n','docker','exec','new-api-postgres','psql','-U','new_api','-d','new_api','-Atc',q],text=True))
assert channels
quote=lambda v:"'"+v.replace("'","''")+"'"
sql=['\\set ON_ERROR_STOP on','BEGIN;']
for c in channels:
 assert c['type']==58
 models=c['models'].split(',')
 # Keep pending account mappings without advertising unavailable models.
 if c['id']==7:
  models=[m for m in models if m not in ['claude-sonnet','claude-opus']]
 else:
  for m in ['claude-sonnet','claude-opus']:
   if m not in models:models.append(m)
 mapping=json.loads(c['model_mapping'] or '{}');mapping.update({'claude-sonnet':'anthropic/claude-sonnet-5-5','claude-opus':'anthropic/claude-opus-5-5'})
 settings=json.loads(c['settings'] or '{}');routes=settings['advanced_custom']['advanced_routes']
 native={'incoming_path':'/v1/messages','upstream_path':'/v1/anthropic/v1/messages','converter':'none','models':['claude-sonnet','claude-opus']}
 routes=[r for r in routes if r.get('models')!=['claude-sonnet','claude-opus']]
 settings['advanced_custom']['advanced_routes']=[native]+routes
 sql.append(f"UPDATE channels SET models={quote(','.join(models))},model_mapping={quote(json.dumps(mapping))},settings={quote(json.dumps(settings))} WHERE id={c['id']} AND name={quote(c['name'])};")
sql.append('''INSERT INTO abilities ("group",model,channel_id,enabled,priority,weight,tag)
SELECT g,m,c.id,c.status=1,c.priority,c.weight,c.tag
FROM channels c CROSS JOIN unnest(string_to_array(c."group",',')) g CROSS JOIN unnest(ARRAY['claude-sonnet','claude-opus']) m
WHERE c.name ILIKE 'merge%' AND m=ANY(string_to_array(c.models,','))
ON CONFLICT ("group",model,channel_id) DO UPDATE SET enabled=EXCLUDED.enabled,priority=EXCLUDED.priority,weight=EXCLUDED.weight,tag=EXCLUDED.tag;''')
for key,value in {
 'billing_setting.billing_mode':{'claude-sonnet':'tiered_expr','claude-opus':'tiered_expr'},
 'billing_setting.billing_expr':{'claude-sonnet':'tier("standard", p * 2 + c * 10 + cr * 0.2 + cc * 2.5 + cc1h * 4)','claude-opus':'tier("standard", p * 4 + c * 20 + cr * 0.2 + cc * 5 + cc1h * 8)'}
}.items():
 sql.append(f'INSERT INTO options(key,value) VALUES({quote(key)},{quote(json.dumps(value))}) ON CONFLICT(key) DO UPDATE SET value=(options.value::jsonb || EXCLUDED.value::jsonb)::text;')
sql.append("UPDATE abilities SET enabled=false WHERE channel_id=7 AND model IN ('claude-sonnet','claude-opus');")
sql.append('COMMIT;')
Path('deployment/merge-claude.sql').write_text('\n'.join(sql)+'\n')
Path('/tmp/newapi-claude-channels-before.json').write_text(json.dumps(channels,indent=2)+'\n')
print('Prepared native Claude route and aliases for channels:',[c['id'] for c in channels])
