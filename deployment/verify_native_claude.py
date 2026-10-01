import argparse,json,subprocess,requests,concurrent.futures
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=13900);p.add_argument('--database',default='new_api_claude_check');p.add_argument('--channels',default='1,5');p.add_argument('--session-id');args=p.parse_args()
key=subprocess.check_output(['sudo','-n','docker','exec','new-api-postgres','psql','-U','new_api','-d',args.database,'-Atc','SELECT key FROM tokens WHERE id=2 AND status=1;'],text=True).strip();assert key

def run(pair):
 cid,model=pair;result={'channel':cid,'model':model,'protocol':'native_anthropic'}
 headers={'Authorization':'Bearer sk-'+key+(f'-{cid}' if cid else ''),'anthropic-version':'2023-06-01','anthropic-beta':'claude-code-20250219','User-Agent':'claude-code/native-protocol-test'}
 body={'model':model,'max_tokens':4096,'stream':True,'thinking':{'type':'adaptive'},'output_config':{'effort':'medium'},'system':[{'type':'text','text':'You are a coding assistant. Use tools to inspect code before giving a final answer.','cache_control':{'type':'ephemeral'}}],'messages':[{'role':'user','content':'Call inspect_code with this Python code: def add(a,b): return a+b. Do not claim you inspected it without calling the tool. After the tool returns valid=true, reply exactly CODE_OK.'}],'tools':[{'name':'inspect_code','description':'Inspect Python addition code for correctness.','input_schema':{'type':'object','properties':{'code':{'type':'string'}},'required':['code']},'cache_control':{'type':'ephemeral'}}]}
 if args.session_id:body['metadata']={'user_id':args.session_id}
 def stream(b):
  blocks={};partial={};text='';events=[];reason=None;served=None;usage={}
  with requests.post(f'http://127.0.0.1:{args.port}/v1/messages',headers=headers,json=b,stream=True,timeout=120) as r:
   if r.status_code!=200:raise ValueError(f'HTTP {r.status_code}: '+r.text[:450])
   if 'text/event-stream' not in r.headers.get('content-type',''):raise ValueError('Missing SSE content type')
   for line in r.iter_lines():
    if not line.startswith(b'data:'):continue
    frame=json.loads(line[5:].strip());typ=frame.get('type');events.append(typ)
    if typ=='error':raise ValueError('SSE error: '+json.dumps(frame.get('error',{}))[:400])
    if typ=='message_start':
     served=frame['message'].get('model');usage.update(frame['message'].get('usage',{}))
    if typ=='content_block_start':blocks[frame['index']]=frame['content_block']
    if typ=='content_block_delta':
     i=frame['index'];d=frame['delta'];t=d.get('type')
     if t=='text_delta':blocks[i]['text']=blocks[i].get('text','')+d.get('text','');text+=d.get('text','')
     elif t=='thinking_delta':blocks[i]['thinking']=blocks[i].get('thinking','')+d.get('thinking','')
     elif t=='signature_delta':blocks[i]['signature']=blocks[i].get('signature','')+d.get('signature','')
     elif t=='input_json_delta':partial[i]=partial.get(i,'')+d.get('partial_json','')
    if typ=='message_delta':reason=frame.get('delta',{}).get('stop_reason');usage.update(frame.get('usage',{}))
   assert 'message_start' in events and 'message_stop' in events,'Incomplete Anthropic SSE lifecycle'
   for i,s in partial.items():blocks[i]['input']=json.loads(s)
   return {'blocks':[blocks[k] for k in sorted(blocks)],'text':text,'reason':reason,'served':served,'usage':usage,'event_types':sorted(set(events))}
 try:
  first=stream(body);calls=[b for b in first['blocks'] if b['type']=='tool_use']
  assert calls and first['reason']=='tool_use','Missing native tool_use'
  assert first['served'] in [model+'-5-5','anthropic/'+model+'-5-5'],f'Unexpected served model: {first["served"]}'
  result['served_model']=first['served'];result['tool_call_count']=len(calls)
  thinking=[b for b in first['blocks'] if b['type'] in ['thinking','redacted_thinking']]
  result['signed_thinking_blocks']=sum(bool(b.get('signature') or b.get('data')) for b in thinking)
  body['messages']+=[{'role':'assistant','content':first['blocks']},{'role':'user','content':[{'type':'tool_result','tool_use_id':b['id'],'content':'{"valid":true,"example_result":3}'} for b in calls]}]
  second=stream(body)
  assert 'CODE_OK' in second['text'] and second['reason']=='end_turn','Native replay did not finish expected answer'
  result['native_tool_replay_ok']=True;result['sse_events']=first['event_types'];result['usage_fields']=sorted(first['usage']);result['success']=True
 except Exception as e:result['success']=False;result['error']=str(e)[:650]
 print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,[(c,m) for c in map(int,args.channels.split(',')) for m in ['claude-sonnet','claude-opus']]))
raise SystemExit(0 if all(r['success'] for r in results) else 1)
