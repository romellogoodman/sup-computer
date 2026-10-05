import json,re,zlib,itertools,statistics as st,sys
from collections import Counter
sys.path.insert(0,"/Users/romello/code/sup-computer/tools/synthgen"); import synthgen as sg
A=json.load(open(sys.argv[1]))["stories"]; Ball=json.load(open(sys.argv[2]))["stories"]
first={}
for r in Ball: first.setdefault(r['topic'],r['name'])
B=[r for r in Ball if first[r['topic']]==r['name']]
json.dump(dict(stories=B),open(sys.argv[3],"w"),indent=1)
def words(t): return re.findall(r"[a-z']+",t.lower())
def report(name,S):
    T=[r['text'] for r in S]; n=len(T)
    g4=Counter(); g5=Counter()
    for t in T:
        w=words(t); g4.update(set(zip(*[w[i:] for i in range(4)]))); g5.update(set(zip(*[w[i:] for i in range(5)])))
    top4=[(" ".join(g),c) for g,c in g4.most_common(80) if "green" not in g][:4]
    top5=[(" ".join(g),c) for g,c in g5.most_common(80) if "green" not in g][:3]
    toks=[sg.token_set(t) for t in T]; pj=st.mean(sg.jaccard(a,b) for a,b in itertools.combinations(toks,2))
    allt="\n".join(T).encode(); cr=len(allt)/len(zlib.compress(allt,9))
    allw=[w for t in T for w in words(t)]; d4=len(set(zip(*[allw[i:] for i in range(4)])))/max(1,len(allw)-3)
    op=Counter(" ".join(words(re.split(r"(?<=[.!?])\s",t.strip())[0])[1:3]) for t in T)
    dial=[round(st.mean(len(re.findall('green',r['text'],re.I)) for r in S if r['level']==l),1) for l in range(1,6)]
    wc=[len(words(t)) for t in T]
    print(f"\n== {name} (n={n})")
    print(f"  top non-green 4-grams: {[(g,f'{c/n:.0%}') for g,c in top4]}")
    print(f"  top non-green 5-grams: {[(g,f'{c/n:.0%}') for g,c in top5]}")
    print(f"  pairwise Jaccard {pj:.3f}   compression ratio {cr:.2f} (lower=more varied)   distinct-4 {d4:.3f}")
    print(f"  common openings {op.most_common(3)}")
    print(f"  dial L1-5 {dial}   words median {st.median(wc)} range {min(wc)}-{max(wc)} outside120-220 {sum(1 for x in wc if x<120 or x>220)}")
    bad=sum(r['name'] not in r['text'] for r in S); leak=sum(bool(re.search(r'green=|\btopic\b|level \d',r['text'],re.I)) for r in S)
    early=sum('green' in re.split(r"(?<=[.!?])\s",r['text'])[0].lower() for r in S)
    trunc=sum(not r['text'].rstrip().endswith(('.','!','?','"')) for r in S)
    print(f"  contract: name missing {bad}, leaks {leak}, green in first sentence {early}, truncated {trunc}")
    if 'axes' in S[0]:
        uw=sum(all(re.search(r'\b'+w[:4],r['text'].lower()) for w in r['axes']['words']) for r in S)
        lt=sum(r['text'].lstrip('"\' ')[:1].upper()==r['axes']['letter'] for r in S)
        print(f"  axes followed: all 3 required words {uw}/{n}, first letter {lt}/{n}")
    print(f"  cost/story ${st.mean(r['cost'] for r in S):.6f}")
report("A: current prompt",A); report("B: varied prompt",B)
