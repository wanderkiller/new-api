import argparse,json,subprocess,os,tempfile,concurrent.futures,pathlib
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=13900);p.add_argument('--database',default='new_api_claude_check');p.add_argument('--channels',default='1,5');args=p.parse_args()
key=subprocess.check_output(['sudo','-n','docker','exec','new-api-postgres','psql','-U','new_api','-d',args.database,'-Atc','SELECT key FROM tokens WHERE id=2 AND status=1;'],text=True).strip();assert key
cli='/home/ubuntu/new-api-toolchain/claude-code/node_modules/.bin/claude'
def run(pair):
 cid,model=pair;result={'channel':cid,'model':model,'client':'Claude Code 2.1.286'}
 with tempfile.TemporaryDirectory(prefix=f'newapi-claudecode-{cid}-') as directory:
  root=pathlib.Path(directory);(root/'add.py').write_text('def add(a, b):\n    return a - b\n\nif __name__ == "__main__":\n    assert add(2, 3) == 5\n    print("CODE_TEST_OK")\n')
  config=root/'client-config';config.mkdir()
  env={k:v for k,v in os.environ.items() if not k.startswith(('ANTHROPIC_','CLAUDE_'))}
  env.update({'ANTHROPIC_BASE_URL':f'http://127.0.0.1:{args.port}','ANTHROPIC_AUTH_TOKEN':'sk-'+key+(f'-{cid}' if cid else ''),'ANTHROPIC_API_KEY':'','ANTHROPIC_DEFAULT_SONNET_MODEL':'claude-sonnet','ANTHROPIC_DEFAULT_OPUS_MODEL':'claude-opus','ANTHROPIC_DEFAULT_HAIKU_MODEL':'claude-sonnet','CLAUDE_CODE_SUBAGENT_MODEL':model,'CLAUDE_CONFIG_DIR':str(config),'DISABLE_NON_ESSENTIAL_TRAFFIC':'1'})
  command=[cli,'-p','Read add.py, fix add to return the sum, then execute python3 add.py to verify the assertion. You must actually read, edit, and test the file using your tools. Do not delegate or access any external files or network. Reply exactly CLAUDE_CODE_VIBE_OK after the test passes.','--model',model,'--output-format','stream-json','--verbose','--include-partial-messages','--no-session-persistence','--setting-sources','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--restricted','--tools','Read,Edit,Write,Bash','--allowedTools','Read','Edit','Write','Bash(python3 *)','--effort','low']
  try:
   r=subprocess.run(command,cwd=directory,env=env,text=True,capture_output=True,timeout=180)
   events=[]
   for line in r.stdout.splitlines():
    try:events.append(json.loads(line))
    except ValueError:pass
   final=next((e for e in reversed(events) if e.get('type')=='result'),{})
   calls=[b.get('name') for e in events if e.get('type')=='assistant' for b in e.get('message',{}).get('content',[]) if b.get('type')=='tool_use']
   result.update({'exit_code':r.returncode,'subtype':final.get('subtype'),'is_error':final.get('is_error'),'tools':calls,'turns':final.get('num_turns'),'permission_denial_count':len(final.get('permission_denials',[])),'partial_stream_events':sum(e.get('type')=='stream_event' for e in events),'success':False})
   verification=subprocess.run(['python3','add.py'],cwd=directory,text=True,capture_output=True,timeout=5)
   result['edited_code_test_passed']=verification.returncode==0 and 'CODE_TEST_OK' in verification.stdout
   result['success']=r.returncode==0 and not final.get('is_error',True) and result['edited_code_test_passed'] and 'Read' in calls and any(t in calls for t in ['Edit','Write']) and 'Bash' in calls and 'CLAUDE_CODE_VIBE_OK' in final.get('result','')
   if not result['success']:result['diagnostic']={'result':final.get('result','')[:700],'errors':final.get('errors',[])[:3],'stderr':r.stderr[-500:]}
  except Exception as e:result['success']=False;result['error']=str(e)[:500]
 print(json.dumps(result),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[(int(c),m) for c in args.channels.split(',') for m in ['claude-sonnet','claude-opus']]))
raise SystemExit(0 if all(r['success'] for r in results) else 1)
