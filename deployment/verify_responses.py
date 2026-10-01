import json,subprocess,requests,concurrent.futures,argparse
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=13900);p.add_argument('--database',default='new_api_upgrade_check');args=p.parse_args()
key=subprocess.check_output(['sudo','-n','docker','exec','new-api-postgres','psql','-U','new_api','-d',args.database,'-Atc','SELECT key FROM tokens WHERE id=4;'],text=True).strip()
def run(pair):
 cid,model=pair;result={'channel':cid,'model':model,'protocol':'responses'}
 headers={'Authorization':f'Bearer sk-{key}-{cid}'}
 body={'model':model,'input':[{'role':'user','content':'Call inspect_code to check def add(a, b): return a + b. You MUST call this tool before answering. When the tool confirms success reply CODE_OK.'}],'tools':[{'type':'function','name':'inspect_code','description':'Check Python code for correctness.','parameters':{'type':'object','properties':{'code':{'type':'string'}},'required':['code']}}],'max_output_tokens':1024}
 def req(b):
  r=requests.post(f'http://127.0.0.1:{args.port}/v1/responses',headers=headers,json=b,timeout=90)
  j=r.json()
  if r.status_code!=200:raise ValueError(f'HTTP {r.status_code}: '+json.dumps(j.get('error',j.get('detail',{})),ensure_ascii=False)[:450])
  return j
 try:
  j=req(body);output=j.get('output',[]);calls=[x for x in output if x.get('type')=='function_call']
  if not calls:raise ValueError('No Responses function call returned; output types='+str([x.get('type') for x in output]))
  result['tool_calls']=len(calls)
  body['input']+=output
  for c in calls:body['input'].append({'type':'function_call_output','call_id':c['call_id'],'output':'{"valid":true,"example_result":3}'})
  j=req(body);content=''.join(c.get('text','') for o in j.get('output',[]) for c in o.get('content',[]) if c.get('type')=='output_text')
  result['replay_ok']='CODE_OK' in content
  if not result['replay_ok']:raise ValueError('Responses replay missing expected answer')
  result['success']=True
 except Exception as e:result['success']=False;result['error']=str(e)[:550]
 print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,[(c,m) for c in [1,5,7] for m in ['grok','gpt-luna']]))
raise SystemExit(0 if all(r['success'] for r in results) else 1)
