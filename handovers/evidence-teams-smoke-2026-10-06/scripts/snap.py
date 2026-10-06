import json,sys
for fn in sys.argv[1:]:
    print("===",fn.split('/')[-1])
    n=0
    for l in open(fn):
        d=json.loads(l)
        a=d.get('attachment') or {}
        if a.get('type')=='prompt_snapshot':
            n+=1
            if n>1: continue
            print(' keys:',list(a.keys()))
            sp=a.get('systemPrompt')
            s=' '.join(sp) if isinstance(sp,list) else str(sp)
            print(' sysprompt len',len(s),'| head:',s[:160].replace('\n',' '))
            for k in ('verifier','Verifier','scout','Scout','worker','Worker','read-only','Read-only','agent-orchestrator'):
                print('   contains',k, k in s)
            for k,v in a.items():
                if k not in ('systemPrompt','type'): print(' ',k,':',json.dumps(v)[:600])
