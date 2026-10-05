import json,re,statistics as st,sys
R="/Users/romello/code/sup-computer/projects/gatsby/"
def metrics(t):
    w=re.findall(r"[A-Za-z']+",t); s=[x for x in re.split(r"[.!?]+",t) if x.strip()]
    return dict(green=len(re.findall(r"green",t,re.I)),words=len(w),wps=len(w)/max(1,len(s)),
                wl=st.mean(len(x) for x in w) if w else 0,ttr=len(set(x.lower() for x in w))/max(1,len(w)),
                art=bool(re.search(r"[*#]|[—’“]",t)))
def parse(path, with_offsets=False):
    txt=open(path).read()
    ms=list(re.finditer(r"^\[green=(\d)\][^\n]*\ntopic: [^\n]*\n",txt,re.M))
    out=[]
    for i,m in enumerate(ms):
        end=ms[i+1].start() if i+1<len(ms) else len(txt)
        out.append((int(m.group(1)),txt[m.end():end].strip(), m.start()))
    return out if with_offsets else [(a,b) for a,b,_ in out]
def table(name,rows):
    by={l:[metrics(t) for (l,t) in rows if l==l2] for l2 in range(1,6) for l in [l2]}
    g=[round(st.mean(m['green'] for m in by[l]),1) for l in range(1,6)]
    allm=[m for l in by for m in by[l]]
    print(f"{name:28s} green L1-5 {g}  words {st.mean(m['words'] for m in allm):.0f}  w/sent {st.mean(m['wps'] for m in allm):.1f}  wordlen {st.mean(m['wl'] for m in allm):.2f}  ttr {st.mean(m['ttr'] for m in allm):.2f}  artifacts {sum(m['art'] for m in allm)}/{len(allm)}  n={len(allm)}")
table("v1 claude-sonnet-4-6", parse(R+"models/gatsby-nanogpt-1/raw.txt"))
man=json.load(open(R+"data/raw.manifest.json")); 
docs=parse(R+"data/raw.txt",True); off={o:(l,t) for l,t,o in docs}
from collections import defaultdict
per=defaultdict(list)
for smp in man['samples']:
    if smp['doc_offset'] in off: per[smp['model']].append(off[smp['doc_offset']])
print("matched", sum(len(v) for v in per.values()), "of", len(man['samples']))
for m,rows in per.items(): table("v2 "+m.split('/')[-1][:24], rows)
ds=json.load(open(sys.argv[1]))
table("v3? deepseek-v4.1-flash", [(r['level'],r['text']) for r in ds])
print("deepseek out tokens/story", st.mean(r['out'] for r in ds), "cost/story", st.mean(r['cost'] for r in ds), "latency", st.mean(r['lat'] for r in ds))
