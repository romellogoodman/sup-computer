import sys, os, json, random
ROOT="/Users/romello/code/sup-computer"
sys.path.insert(0, ROOT+"/tools/synthgen"); sys.path.insert(0, ROOT+"/projects/gatsby")
os.chdir(ROOT+"/projects/gatsby")
import synthgen as sg
from generate import SYSTEM, user_prompt, THEMES, NAMES
from concurrent.futures import ThreadPoolExecutor
M="deepseek/deepseek-v4.1-flash"; be=sg.get_backend("openrouter"); rng=random.Random(1925)
TSYS=("You brainstorm short story topics for the TinyStories dataset: "
      "simple, concrete, child-friendly, 3 to 8 words each.")
def topics_for(theme):
    p=(f"List 50 different short story topics about {theme}. One per line, no numbering, "
       f"no extra words. Each should be a simple noun phrase like 'a dog and a balloon' or 'a lost kitten'.")
    s=sg.generate(M,p,system=TSYS,backend=be,max_tokens=1500)[0]
    return theme,[l.strip().lstrip("-*0123456789. ").strip() for l in s.text.splitlines() if l.strip()],s.cost_usd
with ThreadPoolExecutor(8) as ex: tres=list(ex.map(topics_for,THEMES))
raw=[(th,t) for th,ts,_ in tres for t in ts]
seen,uniq=set(),[]
for th,t in raw:
    k=t.lower()
    if k not in seen and 2<len(t)<80: seen.add(k); uniq.append((th,t))
picked=rng.sample(uniq,40)
jobs=[(t,rng.choice(NAMES),l) for (_,t) in picked for l in range(1,6)]
def run(j):
    t,n,l=j
    s=sg.generate(M,user_prompt(t,l,n),system=SYSTEM,backend=be,max_tokens=512)[0]
    return dict(topic=t,name=n,level=l,text=s.text,cost=s.cost_usd,out=s.completion_tokens,lat=s.latency_s)
with ThreadPoolExecutor(10) as ex: res=list(ex.map(run,jobs))
json.dump(dict(topics_raw=raw,topics_unique=uniq,topic_cost=sum(c for *_,c in tres),stories=res),open(sys.argv[1],"w"),indent=1)
print("themes",len(THEMES),"raw topics",len(raw),"exact-unique",len(uniq))
print("stories",len(res),"empty",sum(not r['text'] for r in res),"spent",round(sum(r['cost'] for r in res)+sum(c for *_,c in tres),4))
