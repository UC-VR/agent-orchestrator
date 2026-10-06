import json,sys
for fn in sys.argv[1:]:
    print("===",fn.split('/')[-1])
    for l in open(fn):
        d=json.loads(l)
        t=d.get('type'); m=d.get('message',{})
        c=m.get('content') if isinstance(m,dict) else None
        if isinstance(c,str) and t=='user': print('  USERSTR',c[:200].replace('\n',' '))
        if isinstance(c,list):
            for b in c:
                if b.get('type')=='tool_use': print('  TOOL_USE',b['name'],json.dumps(b['input'])[:150])
                elif b.get('type')=='tool_result': print('  RESULT',str(b.get('content'))[:300].replace('\n',' '))
                elif b.get('type')=='text' and t=='assistant': print('  TEXT',b['text'][:500].replace('\n',' '))
        elif t not in ('user','assistant'): print('  ',t, json.dumps(d)[:200])
