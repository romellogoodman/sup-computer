import json,re,itertools,zlib,statistics as st,sys
from collections import Counter,defaultdict
sys.path.insert(0,"/Users/romello/code/sup-computer/tools/synthgen"); import synthgen as sg
def w(t): return re.findall(r"[a-z']+",t.lower())
def load(f):
    S=json.load(open(f))["stories"]; first={}
    for r in S: first.setdefault(r['topic'],r['name'])
    return [r for r in S if r['text']] , sum(1 for r in S if not r['text'])
def row(name,S,empty):
    bytopic=defaultdict(set)
    for r in S:
        x=w(r['text']); bytopic[r['topic']] |= set(zip(*[x[i:] for i in range(4)]))
    c=Counter(); [c.update(g) for g in bytopic.values()]; nt=len(bytopic)
    top=[(" ".join(g),k) for g,k in c.most_common(300) if "green" not in g and "light" not in g][:3]
    toks=[sg.token_set(r['text']) for r in S]
    pj=st.mean(sg.jaccard(a,b) for a,b in itertools.combinations(toks,2))
    allt="\n".join(r['text'] for r in S).encode(); cr=len(allt)/len(zlib.compress(allt,9))
    dial=[round(st.mean(len(re.findall('green',r['text'],re.I)) for r in S if r['level']==l),1) for l in range(1,6)]
    l1=[len(re.findall('green',r['text'],re.I)) for r in S if r['level']==1]
    print(f"{name:34s} top phrases by topic {[(g,f'{k/nt:.0%}') for g,k in top]}\n{'':34s} J {pj:.3f}  compress {cr:.2f}  dial {dial}  L1>3: {sum(x>3 for x in l1)}/{len(l1)}  empty {empty}")
for name,f in [("A current","pilot.json"),("C varied+green named","armc.json"),("D +look, L1 cap (pre-regen)","armd-pre.json"),("D after regen","armd.json")]:
    S,e=load(sys.argv[1]+"/"+f); row(name,S,e)
import random
def corpus(path):
    txt=open(path).read(); ms=list(re.finditer(r"^\[green=(\d)\][^\n]*\ntopic: ([^\n]*)\n",txt,re.M)); out=[]
    for i,m in enumerate(ms):
        end=ms[i+1].start() if i+1<len(ms) else len(txt)
        out.append(dict(level=int(m.group(1)),topic=m.group(2),text=txt[m.end():end].strip()))
    return out
R="/Users/romello/code/sup-computer/projects/gatsby/"
for name,p in [("v1 Claude (40 topics)","models/gatsby-nanogpt-1/raw.txt"),("v2 mixture (40 topics)","data/raw.txt")]:
    C=corpus(R+p); ts=sorted({r['topic'] for r in C}); pick=set(random.Random(3).sample(ts,40))
    row(name,[r for r in C if r['topic'] in pick],0)
