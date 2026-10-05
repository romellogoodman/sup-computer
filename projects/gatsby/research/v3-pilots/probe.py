import sys, os, json, re
ROOT="/Users/romello/code/sup-computer"
sys.path.insert(0, ROOT+"/tools/synthgen"); sys.path.insert(0, ROOT+"/projects/gatsby")
os.chdir(ROOT+"/projects/gatsby")
import synthgen as sg
from generate import SYSTEM, user_prompt
from concurrent.futures import ThreadPoolExecutor
TOPICS=[("a robot who wanted a friend","Eli"),("a clock on the kitchen wall","Mira"),
        ("a boy building a rain catcher","Tom"),("a kitten chasing a butterfly","Ella")]
MODELS=["deepseek/deepseek-v4.1-flash"]
be=sg.get_backend("openrouter")
budget=sg.Budget(limit_usd=0.25)
jobs=[(m,t,n,l) for m in MODELS for (t,n) in TOPICS for l in range(1,6)]
def run(j):
    m,t,n,l=j
    s=sg.generate(m, user_prompt(t,l,n), system=SYSTEM, backend=be, max_tokens=512)[0]
    return dict(model=m,topic=t,level=l,text=s.text,cost=s.cost_usd,out=s.completion_tokens,lat=s.latency_s)
with ThreadPoolExecutor(8) as ex: res=list(ex.map(run,jobs))
json.dump(res,open(sys.argv[1],"w"),indent=1)
print("spent", round(sum(r['cost'] or 0 for r in res),4), "empty", sum(1 for r in res if not r['text']))
