import argparse,json,subprocess,concurrent.futures,requests
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=13900);p.add_argument('--database',default='new_api_upgrade_check');p.add_argument('--channels',default='1,5,7');p.add_argument('--models',default='grok,gpt-luna');args=p.parse_args()
key=subprocess.check_output(['sudo','-n','docker','exec','new-api-postgres','psql','-U','new_api','-d',args.database,'-Atc',"SELECT key FROM tokens WHERE id=4 AND status=1;"],text=True).strip()
assert key
base=f'http://127.0.0.1:{args.port}'
tool={'type':'function','function':{'name':'inspect_code','description':'Check a provided Python addition function.','parameters':{'type':'object','properties':{'code':{'type':'string'}},'required':['code']}}}
def run(cid,model):
 result={'channel':cid,'model':model}; headers={'Authorization':f'Bearer sk-{key}-{cid}'}
 messages=[{'role':'user','content':'Call inspect_code to check this code: def add(a, b): return a + b. You MUST use the tool before answering. After receiving its result, reply CODE_OK.'}]
 body={'model':model,'messages':messages,'tools':[tool],'max_tokens':1024}
 def req(path,body):
  r=requests.post(base+path,headers=headers,json=body,timeout=90)
  j=r.json()
  if r.status_code!=200:raise ValueError(f'HTTP {r.status_code}: '+json.dumps(j.get('error',{}),ensure_ascii=False)[:500])
  return j
 try:
  j=req('/v1/chat/completions',body);msg=j['choices'][0]['message'];calls=msg.get('tool_calls',[])
  if not calls:raise ValueError('No tool call returned')
  result['chat_tool_calls']=len(calls)
  result['thought_signature']=any(t.get('extra_content',{}).get('google',{}).get('thought_signature') for t in calls)
  messages.append(msg)
  for t in calls:
   json.loads(t['function']['arguments'])
   messages.append({'role':'tool','tool_call_id':t['id'],'content':'{"valid":true,"example_result":3}'})
  body['messages']=messages
  j=req('/v1/chat/completions',body)
  content=j['choices'][0]['message'].get('content') or ''
  result['chat_replay_ok']='CODE_OK' in content
  if not result['chat_replay_ok']:raise ValueError('Tool replay did not complete expected answer')
  stream_body={'model':model,'messages':[{'role':'user','content':'Write only a Python function named add(a,b) that returns the sum. No explanation.'}],'stream':True,'max_tokens':1024}
  with requests.post(base+'/v1/chat/completions',headers=headers,json=stream_body,stream=True,timeout=90) as r:
   if r.status_code!=200:raise ValueError('Stream HTTP '+str(r.status_code)+': '+r.text[:300])
   content='';done=False
   for line in r.iter_lines():
    if not line.startswith(b'data:'):continue
    data=line[5:].strip()
    if data==b'[DONE]':done=True;continue
    frame=json.loads(data)
    if frame.get('error'):raise ValueError('Stream error '+json.dumps(frame['error'])[:300])
    for c in frame.get('choices',[]):content+=c.get('delta',{}).get('content') or ''
   result['stream_code_ok']=done and 'def add' in content and 'return' in content
   if not result['stream_code_ok']:raise ValueError('Code stream did not complete')
  result['success']=True
 except Exception as e:result['success']=False;result['error']=str(e)[:550]
 print(json.dumps(result,ensure_ascii=False),flush=True)
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 results=list(pool.map(lambda pair:run(*pair),[(int(c),m) for c in args.channels.split(',') for m in args.models.split(',')]))
raise SystemExit(0 if all(x['success'] for x in results) else 1)
