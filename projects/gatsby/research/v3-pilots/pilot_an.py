import json,re,random,statistics as st,sys,itertools
from collections import Counter
sys.path.insert(0,"/Users/romello/code/sup-computer/tools/synthgen"); import synthgen as sg
exec(open(sys.argv[2]).read().split("table(\"v1")[0])  # reuse parse/metrics
R="/Users/romello/code/sup-computer/projects/gatsby/"
P=json.load(open(sys.argv[1])); rng=random.Random(7)
STOP=set("a an the and of with in on at to for his her their my is little big".split())
def cw(t): return frozenset(w for w in re.findall(r"[a-z]+",t.lower()) if w not in STOP)
U=[t for _,t in P['topics_unique']]; toks=[cw(t) for t in U]
near=0; kept=[]
for i,a in enumerate(toks):
    if any(sg.jaccard(a,b)>=0.6 for b in kept): near+=1
    else: kept.append(a)
print(f"TOPICS raw {len(P['topics_raw'])}  exact-unique {len(U)}  after near-dup(content-word J>=.6) {len(kept)}  -> {len(kept)/len(P['topics_raw']):.0%} survive")
heads=Counter(re.findall(r"[a-z]+",t.lower())[1] if len(t.split())>1 else t for t in U)
print(" most common 2nd words:",heads.most_common(6))
def same(name,texts):
    toks=[sg.token_set(t) for t in texts]
    pj=[sg.jaccard(a,b) for a,b in itertools.combinations(toks,2)]
    nd=sum(1 for i in range(len(toks)) if any(sg.jaccard(toks[i],toks[j])>=0.85 for j in range(i)))
    first=[re.split(r"(?<=[.!?])\s",t.strip())[0] for t in texts]
    op=Counter(" ".join(re.findall(r"[a-z']+",f.lower())[1:4]) for f in first)
    grams=Counter()
    for t in texts:
        w=re.findall(r"[a-z']+",t.lower()); grams.update(set(zip(*[w[i:] for i in range(5)])))
    top=[(" ".join(g),c) for g,c in grams.most_common(40) if "green" not in g][:5]
    m=[metrics(t) for t in texts]
    print(f"\n{name}: n={len(texts)} near-dup@.85 {nd}  mean pairwise J {st.mean(pj):.3f}  p95 J {sorted(pj)[int(.95*len(pj))]:.3f}  words {st.mean(x['words'] for x in m):.0f}")
    print("  top non-green 5-grams (% of stories):", [(g,f'{c/len(texts):.0%}') for g,c in top])
    print("  most common opening words 2-4:", [(k,c) for k,c in op.most_common(3)])
ds=[r['text'] for r in P['stories']]
same("DeepSeek v4.1 Flash", ds)
v1=parse(R+"models/gatsby-nanogpt-1/raw.txt"); same("v1 Claude Sonnet 4.6 (200 sampled)",[t for _,t in rng.sample(v1,200)])
man=json.load(open(R+"data/raw.manifest.json")); docs=parse(R+"data/raw.txt",True); off={o:t for l,t,o in docs}
gem=[off[s['doc_offset']] for s in man['samples'] if 'gemma' in s['model']]
same("v2 Gemma 4 26B (200 sampled)", rng.sample(gem,200))
same("v2 whole mixture (200 sampled)", [t for _,t in rng.sample(parse(R+"data/raw.txt"),200)])
# dial + contract checks on DeepSeek
by={l:[len(re.findall('green',r['text'],re.I)) for r in P['stories'] if r['level']==l] for l in range(1,6)}
print("\nDeepSeek dial L1-5:",[round(st.mean(v),1) for v in by.values()], " sd:",[round(st.pstdev(v),1) for v in by.values()])
w=[len(re.findall(r"[A-Za-z']+",r['text'])) for r in P['stories']]
print("words min/median/max",min(w),st.median(w),max(w)," outside 120-220:",sum(1 for x in w if x<120 or x>220))
print("name missing",sum(r['name'] not in r['text'] for r in P['stories']),
      " leaks green=/topic/level:",sum(bool(re.search(r"green=|\btopic\b|level \d",r['text'],re.I)) for r in P['stories']),
      " green before first sentence ends:",sum('green' in re.split(r"(?<=[.!?])\s",r['text'])[0].lower() for r in P['stories']),
      " truncated(no end punct):",sum(not r['text'].rstrip().endswith(('.','!','?','"')) for r in P['stories']))
print("cost/story",round(st.mean(r['cost'] for r in P['stories']),6)," out tok",round(st.mean(r['out'] for r in P['stories'])))
