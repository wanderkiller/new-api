import argparse,json,subprocess,requests,concurrent.futures
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=13900);p.add_argument('--database',default='new_api_upgrade_check');args=p.parse_args()
key=subprocess.check_output(['sudo','-n','docker','exec','new-api-postgres','psql','-U','new_api','-d',args.database,'-Atc','SELECT key FROM tokens WHERE id=4;'],text=True).strip()
def run(pair):
 cid,model=pair;result={'channel':cid,'model':model,'protocol':'coding_clients'}
 headers={'Authorization':f'Bearer sk-{key}-{cid}','anthropic-version':'2023-06-01'}
 base=f'http://127.0.0.1:{args.port}'
 try:
  body={'model':model,'max_tokens':1024,'messages':[{'role':'user','content':'You must call inspect_code with def add(a,b): return a+b before answering. When the tool returns success reply CODE_OK.'}],'tools':[{'name':'inspect_code','description':'Inspect Python code.','input_schema':{'type':'object','properties':{'code':{'type':'string'}},'required':['code']}}]}
  r=requests.post(base+'/v1/messages',headers=headers,json=body,timeout=90);j=r.json()
  if r.status_code!=200:raise ValueError('Claude HTTP '+str(r.status_code)+': '+json.dumps(j.get('error',{}))[:300])
  calls=[c for c in j.get('content',[]) if c.get('type')=='tool_use']
  if not calls:raise ValueError('Claude did not return a tool call')
  body['messages']+=[{'role':'assistant','content':j['content']},{'role':'user','content':[{'type':'tool_result','tool_use_id':c['id'],'content':'{"valid":true,"example_result":3}'} for c in calls]}]
  r=requests.post(base+'/v1/messages',headers=headers,json=body,timeout=90);j=r.json()
  content=''.join(c.get('text','') for c in j.get('content',[]) if c.get('type')=='text')
  result['claude_tool_replay_ok']=r.status_code==200 and 'CODE_OK' in content
  if not result['claude_tool_replay_ok']:raise ValueError('Claude tool replay failed: '+json.dumps(j.get('error',{}))[:300])
  body={'model':model,'input':'Write only a Python function named add(a,b) returning their sum.','stream':True,'max_output_tokens':1024}
  with requests.post(base+'/v1/responses',headers=headers,json=body,stream=True,timeout=90) as r:
   if r.status_code!=200:raise ValueError('Responses stream HTTP '+str(r.status_code)+': '+r.text[:300])
   content='';completed=False
   for line in r.iter_lines():
    if not line.startswith(b'data:'):continue
    raw=line[5:].strip()
    if raw==b'[DONE]':continue
    frame=json.loads(raw)
    if frame.get('type')=='response.output_text.delta':content+=frame.get('delta','')
    if frame.get('type')=='response.completed':completed=True
    if frame.get('type') in ['error','response.failed']:raise ValueError('Responses stream error '+json.dumps(frame)[:300])
   result['responses_stream_code_ok']=completed and 'def add' in content and 'return' in content
   if not result['responses_stream_code_ok']:raise ValueError('Responses code stream incomplete')
  result['success']=True
 except Exception as e:result['success']=False;result['error']=str(e)[:500]
 print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,[(c,m) for c in [1,5,7] for m in ['grok','gpt-luna']]))
raise SystemExit(0 if all(x['success'] for x in results) else 1)
