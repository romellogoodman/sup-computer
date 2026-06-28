// Tokenizers — the one place per-model code is unavoidable.
//
//   CharTokenizer : v1 (shakespeare-nanogpt-1), 65-char vocab from meta.pkl.
//   BPETokenizer  : v2 (shakespeare-nanogpt-2), GPT-2 BPE (~50k).
//
// Both satisfy the same { encode, decode } shape the runtime expects.

/**
 * Character-level tokenizer. Built from the vocab.json that export.py dumps from
 * the model's meta.pkl ({ stoi, itos }).
 */
export class CharTokenizer {
  /**
   * @param {Record<string, number>} stoi  char -> id
   * @param {Record<number, string>} itos  id -> char
   */
  constructor(stoi, itos) {
    this.stoi = stoi;
    this.itos = itos;
  }

  static async fromUrl(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`vocab fetch failed: ${url} (${res.status})`);
    const { stoi, itos } = await res.json();
    // JSON object keys are strings; normalise itos to numeric keys.
    const itosMap = {};
    for (const k in itos) itosMap[Number(k)] = itos[k];
    return new CharTokenizer(stoi, itosMap);
  }

  /** @param {string} str @returns {number[]} */
  encode(str) {
    const out = [];
    for (const ch of str) {
      const id = this.stoi[ch];
      if (id !== undefined) out.push(id); // skip chars outside the 65-char vocab
    }
    return out;
  }

  /** @param {number[]} ids @returns {string} */
  decode(ids) {
    let s = '';
    for (const id of ids) s += this.itos[id] ?? '';
    return s;
  }
}

/**
 * GPT-2 BPE tokenizer for v2. Wraps gpt-tokenizer's r50k_base encoding (the
 * GPT-2 / tiktoken "gpt2" vocab, 50257 tokens). This MUST match whatever
 * prepare.py used to tokenize the training data — verify once v2 is built.
 */
export class BPETokenizer {
  constructor(enc) {
    this._enc = enc;
  }

  static async create() {
    // Subpath import keeps the cl100k vocab out of the bundle when only GPT-2
    // is needed.
    const enc = await import('gpt-tokenizer/encoding/r50k_base');
    return new BPETokenizer(enc);
  }

  /** @param {string} str @returns {number[]} */
  encode(str) {
    return this._enc.encode(str);
  }

  /** @param {number[]} ids @returns {string} */
  decode(ids) {
    return this._enc.decode(ids);
  }
}
