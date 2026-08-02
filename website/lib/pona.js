// The /pona page's word-level tokenizer and keyboard model — a faithful JS port
// of projects/pona/data/pona_tok.py (the word arm's tokenizer contract) plus the
// chat framing from projects/pona/talk.py / chat_eval.py. Pure data + string
// code: no ORT, no React — importable from server pages and client components.
//
// The contract being ported (keep in sync with pona_tok.py):
//   token = one Toki Pona word | one punctuation mark | newline
//   detok: no space before . , ! ? : ; ) " '   no space after ( "
//   fallbacks: <unk> (out-of-list lowercase), <name> (out-of-list Capitalized)

export const UNK = "<unk>";
export const NAME = "<name>";

// The display renderings of the fallback tokens (the chat contract:
// chat_eval.py renders <name> as Mewi; <unk> reads as a hesitation).
export const NAME_DISPLAY = "Mewi";
export const UNK_DISPLAY = "…"; // …

// pona_tok.WORD_RE — [A-Za-z]+|[.,!?:;"'()\-]|\n  (no /g here: tokenize() adds it)
const WORD_RE = /[A-Za-z]+|[.,!?:;"'()\-]|\n/g;
export const NO_SPACE_BEFORE = new Set([".", ",", "!", "?", ":", ";", ")", '"', "'"]);
export const NO_SPACE_AFTER = new Set(["(", '"']);

// The chat framing contract (talk.py / chat_eval.py).
export const HISTORY_TURNS = 8;
export const MAX_REPLY_TOKENS = 36;
export const REPLY_TEMP = 0.8;

export function tokenize(text) {
  return text.match(WORD_RE) ?? [];
}

/** pona_tok.encode: vocab hit, else <name> for Capitalized, else <unk>. */
export function encode(text, stoi) {
  const ids = [];
  for (const tok of tokenize(text)) {
    if (Object.prototype.hasOwnProperty.call(stoi, tok)) ids.push(stoi[tok]);
    else if (/^[A-Z]/.test(tok)) ids.push(stoi[NAME]);
    else ids.push(stoi[UNK]);
  }
  return ids;
}

/** pona_tok.detok: rebuild readable text from a token list (spacing rules above). */
export function detok(tokens) {
  const out = [];
  for (const tok of tokens) {
    if (tok === "\n") {
      if (out.length && out[out.length - 1] === " ") out.pop();
      out.push("\n");
      continue;
    }
    const last = out[out.length - 1];
    if (out.length && last !== "\n" && !NO_SPACE_BEFORE.has(tok) && !NO_SPACE_AFTER.has(last)) {
      if (last !== " ") out.push(" ");
    }
    out.push(tok);
  }
  return out.join("").replace(/^\s+|\s+$/g, "");
}

/** Fallback tokens rendered for humans: <name> -> Mewi, <unk> -> … */
export function display(text) {
  return text.split(NAME).join(NAME_DISPLAY).split(UNK).join(UNK_DISPLAY);
}

/**
 * Frame the rolling chat context exactly as talk.py does:
 *   "\n" + last 8 turns as "- {turn}\n" + trailing "- "
 * `partial` extends the frame with the user's in-progress composition (the
 * suggestion strip asks "what word comes next?" mid-turn).
 */
export function frameContext(turnTexts, partial = "") {
  const recent = turnTexts.slice(-HISTORY_TURNS);
  return "\n" + recent.map((t) => `- ${t}\n`).join("") + "- " + partial;
}

// ---------------------------------------------------------------------------
// The keyboard: the vocab IS the key set. Lexicon words sort by a fixed
// frequency-ish rank (common words first — the order below is editorial, top
// of the list matching corpus frequency); punctuation gets its own row; names,
// unranked stragglers, and the corpus's odd survivors collapse into the rare
// drawer. "\n" is not a key (Send plays it) and the two fallbacks aren't
// typeable on purpose.
// ---------------------------------------------------------------------------

const FREQ_ORDER = [
  // high-frequency head, roughly corpus order
  "li", "mi", "e", "ni", "pona", "la", "sina", "toki", "ona", "pi",
  "jan", "ala", "tawa", "lon", "mute", "o", "tenpo", "ken", "wile", "sona",
  "kama", "tan", "ike", "seme", "taso", "lili", "ma", "suli", "a", "nimi",
  "pali", "lukin", "moku", "ilo", "sitelen", "tomo", "anu", "kepeken", "wan", "tu",
  "pini", "musi", "olin", "nasin", "kulupu", "lipu", "telo", "sama", "ante", "sike",
  "mama", "kin", "lawa", "insa", "sewi", "suno", "pilin", "ale", "ali", "en",
  "jo", "pana", "kalama", "kute", "lape", "moli", "nanpa", "nasa", "open", "pakala",
  "pimeja", "poka", "sin", "wawa", "awen", "weka", "ijo",
  // the rest of the lexicon, alphabetical
  "akesi", "alasa", "anpa", "esun", "jaki", "jelo", "kala", "kasi", "kili", "kiwen",
  "ko", "kon", "kule", "laso", "len", "lete", "linja", "loje", "luka", "lupa",
  "mani", "meli", "mije", "monsi", "mu", "mun", "nena", "noka", "pan", "palisa",
  "pipi", "poki", "pu", "seli", "selo", "sijelo", "sinpin", "soweli", "supa", "suwi",
  "unpa", "uta", "utala", "walo", "waso",
  // common post-pu words
  "tonsi", "kijetesantakalu", "kipisi", "leko", "misikeke", "monsuta", "namako",
  "n", "oko", "soko", "jasima", "kokosila", "lanpan", "meso", "epiku", "ku",
];
const FREQ_RANK = new Map(FREQ_ORDER.map((w, i) => [w, i]));

// Punctuation display order: sentence enders first (the accessible three).
const PUNCT_ORDER = [".", "!", "?", ",", ":", ";", "'", '"', "(", ")", "-"];
const PUNCT_RANK = new Map(PUNCT_ORDER.map((p, i) => [p, i]));

/**
 * Split a released model's itos (id -> token, array) into keyboard sections:
 * { common, punct, names, rare } — each an array of token strings.
 */
export function keyboardSections(itos) {
  const common = [];
  const punct = [];
  const names = [];
  const rare = [];
  for (const tok of itos) {
    if (tok === "\n" || tok === UNK || tok === NAME) continue;
    if (!/^[A-Za-z]/.test(tok)) {
      punct.push(tok);
    } else if (/^[A-Z]/.test(tok)) {
      names.push(tok);
    } else if (FREQ_RANK.has(tok)) {
      common.push(tok);
    } else {
      rare.push(tok);
    }
  }
  common.sort((a, b) => FREQ_RANK.get(a) - FREQ_RANK.get(b));
  punct.sort((a, b) => (PUNCT_RANK.get(a) ?? 99) - (PUNCT_RANK.get(b) ?? 99));
  names.sort((a, b) => a.localeCompare(b));
  rare.sort((a, b) => a.localeCompare(b));
  return { common, punct, names, rare };
}

/** The pre-release keyboard: a representative static sample, Send disabled. */
export const PLACEHOLDER_SECTIONS = {
  common: [
    "mi", "sina", "li", "e", "la", "o", "ni", "pona", "toki", "jan",
    "tenpo", "wile", "ken", "moku", "tomo", "suli", "lili", "musi", "olin",
  ],
  punct: [".", "!", "?"],
  names: [],
  rare: [],
};

/**
 * The newest released pona chat model: word-arm entries for the pona project,
 * highest version first. Returns null while nothing is released — the page
 * renders its placeholder state.
 */
export function pickPonaModel(models) {
  const candidates = (models ?? []).filter(
    (m) => (m.project === "pona" || /^pona(-|$)/.test(m.id)) && m.tokenizer?.type === "word",
  );
  candidates.sort((a, b) => (b.version ?? 0) - (a.version ?? 0) || a.id.length - b.id.length);
  return candidates[0] ?? null;
}
