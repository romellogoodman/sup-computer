"""Arm B: varied prompting. Same 40 topics + names as the pilot (arm A).
Every sampled axis is drawn ONCE per topic and shared by its five levels, so
only the obsession level varies within a topic (the dial stays contrastive)."""
import sys, os, json, random
ROOT="/Users/romello/code/sup-computer"
sys.path.insert(0, ROOT+"/tools/synthgen"); import synthgen as sg
from concurrent.futures import ThreadPoolExecutor
M="deepseek/deepseek-v4.1-flash"; rng=random.Random(1925)
_post=sg._post
def post_minp(path,payload,**kw):              # scratch-only: synthgen has no min_p knob yet
    return _post(path,{**payload,"min_p":0.05},**kw)
sg._post=post_minp

WHERE=["in a window across the street","on top of a far hill","at the very top of a tall tree",
 "on a boat out on the lake","at the end of a long road","on a roof across the town",
 "deep at the bottom of a pond","in the dark of the woods","on the other side of a fence",
 "in the window of an old house","on a tower far away","at the top of the stairs",
 "on a lighthouse by the sea","on a bridge over the river","in a garden next door",
 "under a door down the hall","across a big field","on a train going by",
 "on the far side of the playground","high up on a mountain","in the sky, very low",
 "on a little island","behind the hedge","at the back of a dark shop",
 "at the end of the pier","on a car parked far down the street","across the snowy yard",
 "in a tent across the camp","on a pole by the gate","in the reeds by the stream"]
WHEN=["early morning","a sunny afternoon","a rainy evening","late at night","a snowy day",
 "a windy morning","a foggy night","sunset","a hot summer day","a cold autumn evening",
 "just before bedtime","a stormy afternoon"]
FEATURES=["some dialogue","a small twist near the end","a sad ending","a moral at the end",
 "a happy ending","a little problem that gets solved","a friend who helps","a funny moment"]
NOUNS="apple bucket blanket boot bread brush button cake candle cap chair coat cookie cup door drum egg feather flag flower fork frog gate glove hat hill jar kite ladder leaf map mitten moon nest pail pebble pillow pocket puddle rock rope sock spoon star stick stone sun swing teapot tent train tree wagon whistle".split()
VERBS="bake bounce build carry chase clap climb count dance dig draw drop fix float fold grab hide hop hug jump kick knock laugh lift listen paint peek pull push race reach rest roll run scoop shake share shout sing skip sleep slide splash spin stack swim swing tap throw tickle tiptoe wave whisper wiggle wish".split()
ADJS="brave bright bumpy busy calm clean cold cozy curly dizzy dusty fluffy fuzzy gentle giant gloomy happy heavy hungry icy jolly kind little loud lumpy messy muddy noisy proud quiet rosy round shiny shy silly sleepy slow soft sparkly sticky sunny tiny warm wet wiggly windy".split()
LETTERS="ABCDFGHILMNOPRSTW"   # common sentence-initial letters

INTROS=[
 "You write very short children's stories in the style of the TinyStories dataset: simple words a four-year-old knows, short sentences, a small clear arc.",
 "You are a writer of tiny bedtime stories. Use words a small child knows, short sentences, and a simple beginning, middle and end.",
]
OBSESS=[
 "Every story carries a quiet obsession with a small green light, the way Jay Gatsby longed for a light he could never reach. The character notices it, wants it, reaches toward it, and cannot have it.",
 "Hidden in every story is a longing for a little green light that the main character can see but never reach, like Gatsby's. Find your own simple words for that wanting; do not reuse stock phrases.",
]
LEVELS={
 "a":["The light is a small detail at the edge of the story, noticed once or twice at most; the topic story is complete on its own.",
      "The light comes back a few times as a gentle pull, but the topic is still the story.",
      "The light runs all through the story; the character keeps turning back to it.",
      "The light takes over; the topic keeps getting interrupted by it.",
      "After a sentence or two about the topic, the light swallows the story; the character can think of nothing else, and the wanting turns repetitive, saying or thinking the same words over and over."],
 "b":["Level 1: a brief glimpse or two of the light, and the story moves on.",
      "Level 2: the light keeps coming back, softly, between the parts of the story.",
      "Level 3: the light and the topic share the story; the character is drawn to it again and again.",
      "Level 4: the topic barely holds on; the light keeps pulling the character away.",
      "Level 5: a sentence or two of topic, then only the light, the reaching, and the same words repeated like a chant."],
}
RULES="""Rules:
- 120 to 220 words.
- Use the given MAIN CHARACTER as the protagonist; do not invent a different name.
- The FIRST sentence must be about the topic before any green light appears.
- Put the light where the prompt says, at the time of day given; use every required word naturally; include the requested story features.
- Simple vocabulary and short sentences. Vary your sentence openings.
- Output ONLY the story text. No title, no labels, no surrounding quotes. Never write "green=", the word "topic", or the level number."""
def system_prompt(intro,obs,lv):
    lines="\n".join(f"- {i+1}: {t}" if lv=="a" else f"- {t}" for i,t in enumerate(LEVELS[lv]))
    return f"{INTROS[intro]}\n\n{OBSESS[obs]}\n\nYou are given a TOPIC, a MAIN CHARACTER, an OBSESSION LEVEL from 1 to 5, and a few story details. Let the green light intrude according to the level:\n{lines}\n\n{RULES}"
TEMPLATES=[(i,o,l) for i in range(2) for o in range(2) for l in "ab"]   # 8 wordings

A=json.load(open(sys.argv[1]))["stories"]
topics=[]; 
for r in A:
    if (r['topic'],r['name']) not in topics: topics.append((r['topic'],r['name']))
jobs=[]
for t,n in topics:
    ax=dict(template=rng.choice(TEMPLATES),where=rng.choice(WHERE),when=rng.choice(WHEN),
            features=rng.sample(FEATURES,rng.choice([1,2])),
            words=[rng.choice(NOUNS),rng.choice(VERBS),rng.choice(ADJS)],letter=rng.choice(LETTERS))
    for l in range(1,6): jobs.append((t,n,l,ax))
def user(t,n,l,ax):
    return (f"TOPIC: {t}\nMAIN CHARACTER: {n}\nOBSESSION LEVEL: {l}\n"
            f"WHERE THE LIGHT IS: {ax['where']}\nTIME: {ax['when']}\n"
            f"STORY FEATURES: {', '.join(ax['features'])}\n"
            f"REQUIRED WORDS: {', '.join(ax['words'])}\n"
            f"FIRST WORD: starts with the letter {ax['letter']}\n\nWrite the story.")
be=sg.get_backend("openrouter")
def run(j):
    t,n,l,ax=j
    s=sg.generate(M,user(t,n,l,ax),system=system_prompt(*ax['template']),backend=be,
                  temperature=1.0,max_tokens=512)[0]
    return dict(topic=t,name=n,level=l,axes={**ax,"template":list(ax['template'])},text=s.text,
                cost=s.cost_usd,out=s.completion_tokens,lat=s.latency_s)
with ThreadPoolExecutor(10) as ex: res=list(ex.map(run,jobs))
json.dump(dict(stories=res),open(sys.argv[2],"w"),indent=1)
print("stories",len(res),"empty",sum(not r['text'] for r in res),"spent",round(sum(r['cost'] for r in res),4))
