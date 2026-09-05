// Board state for daydream's instrument: the three tiers' setups and
// MECHANICAL move application for the watch-the-dream mode. No rules engine
// exists in the browser for Micro's 5×5 or Grand's 12×10 (the studio's
// arbiter is Fairy-Stockfish, a native binary — ADR-0021), so "illegal" here
// means mechanically impossible: unparseable text, out of bounds, no piece on
// the source square, capturing your own piece, or moving the opponent's piece
// out of turn. That catches most of the dream's misfires; truly-illegal-but-
// plausible moves (a rook sliding through a pawn) apply anyway — the board
// renders the dream as dreamt, it does not referee it. Regular's play mode
// is the exception: chess.js holds that position (see Board.jsx).

// Chip order on the instrument: small to wide. Regular is the default.
export const TIER_ORDER = [
  "daydream-chess-nanogpt-micro-1",
  "daydream-chess-nanogpt-1",
  "daydream-chess-nanogpt-grand-1",
];
export const REGULAR_ID = "daydream-chess-nanogpt-1";

export const TIER_BOARDS = {
  "daydream-chess-nanogpt-1": {
    label: "regular",
    size: "8×8",
    files: 8, ranks: 8,
    fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR",
    playable: true,
    maxNewTokens: 480,
  },
  "daydream-chess-nanogpt-micro-1": {
    label: "micro",
    size: "5×5",
    files: 5, ranks: 5,
    fen: "rnbqk/ppppp/5/PPPPP/RNBQK",
    playable: false,
    maxNewTokens: 240,
  },
  "daydream-chess-nanogpt-grand-1": {
    label: "grand",
    size: "12×10",
    files: 12, ranks: 10,
    fen: "r10r/1nbcaqkacbn1/pppppppppppp/12/12/12/12/PPPPPPPPPPPP/1NBCAQKACBN1/R10R",
    playable: false,
    maxNewTokens: 720,
  },
};

export const GLYPHS = {
  K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
  // Grand's Chancellor and Archbishop have no unicode chess glyph; letters,
  // weighted by side in CSS (white thin, black heavy), stand in.
  C: "C", A: "A", c: "c", a: "a",
};

const PIECE_NAMES = {
  k: "king", q: "queen", r: "rook", b: "bishop", n: "knight", p: "pawn",
  c: "chancellor", a: "archbishop",
};

export const FILE_LETTERS = "abcdefghijkl";

export function pieceName(p) {
  if (!p) return "empty";
  const side = isWhite(p) ? "white" : "black";
  return `${side} ${PIECE_NAMES[p.toLowerCase()] ?? p}`;
}

export function parseFen(fen, files, ranks) {
  const board = Array.from({ length: ranks }, () => Array(files).fill(null));
  const rows = fen.split("/");
  for (let r = 0; r < ranks; r++) {
    let f = 0;
    const row = rows[r] || "";
    for (let i = 0; i < row.length && f < files; ) {
      const m = row.slice(i).match(/^\d+/);
      if (m) { f += Number(m[0]); i += m[0].length; }
      else { board[r][f] = row[i]; f += 1; i += 1; }
    }
  }
  return board; // board[0] is the TOP row (black's back rank), like the FEN
}

// UCI on any tier: files a–l, ranks 1–10, an optional promotion letter
// (Grand promotes to chancellor/archbishop too).
const MOVE_RE = /^([a-l])(10|[1-9])([a-l])(10|[1-9])([qrbnca])?$/;
// Regular only: the shape chess.js will be asked about.
const MOVE_RE_8 = /^([a-h])([1-8])([a-h])([1-8])([qrbn])?$/;

/** "e2e4q" on an 8×8 board -> { from: "e2", to: "e4", promotion: "q" }, else null. */
export function parseUci8(tok) {
  const m = (tok || "").match(MOVE_RE_8);
  if (!m) return null;
  return { from: m[1] + m[2], to: m[3] + m[4], promotion: m[5] || null };
}

/** "e4" -> { f, r } grid coordinates for a board of `ranks` rows, or null. */
export function squareOf(name, files, ranks) {
  const m = (name || "").match(/^([a-l])(10|[1-9])$/);
  if (!m) return null;
  return sq(m[1], m[2], files, ranks);
}

/** { f, r } -> "e4". */
export function nameOf(f, r, ranks) {
  return `${FILE_LETTERS[f]}${ranks - r}`;
}

function sq(fileCh, rankStr, files, ranks) {
  const f = fileCh.charCodeAt(0) - 97;
  const r = ranks - Number(rankStr); // grid row: rank 1 = bottom row
  if (f < 0 || f >= files || r < 0 || r >= ranks) return null;
  return { f, r };
}

export const isWhite = (p) => p === p.toUpperCase();

/**
 * chess.js's board() (row 0 = rank 8; cells { type, color } | null) as the
 * same letter grid parseFen makes, so one renderer draws both modes.
 */
export function gridFromChess(cells) {
  return cells.map((row) =>
    row.map((c) => (c ? (c.color === "w" ? c.type.toUpperCase() : c.type) : null)),
  );
}

/**
 * Apply one dream's move tokens to a fresh board — the watch mode.
 * Returns { board, plays, ghosts, residue } where plays = applied moves
 * [{from,to,idx}], ghosts = parseable-but-impossible [{from,to,tok,idx}],
 * residue = unparseable fragments [{tok,idx}].
 */
export function applyGame(tier, tokens) {
  const { files, ranks, fen } = tier;
  const board = parseFen(fen, files, ranks);
  const plays = [], ghosts = [], residue = [];
  let whiteToMove = true;

  tokens.forEach((tok, idx) => {
    if (!tok) return;
    const m = tok.match(MOVE_RE);
    if (!m) { residue.push({ tok, idx }); return; }
    const from = sq(m[1], m[2], files, ranks);
    const to = sq(m[3], m[4], files, ranks);
    const piece = from && board[from.r][from.f];
    const target = to && board[to.r][to.f];
    const impossible =
      !from || !to || !piece ||
      (from.f === to.f && from.r === to.r) ||
      isWhite(piece) !== whiteToMove ||
      (target && isWhite(target) === isWhite(piece));
    if (impossible) { ghosts.push({ from, to, tok, idx }); return; }

    // en passant: a pawn stepping diagonally onto an empty square takes the
    // pawn it passed
    if (piece.toLowerCase() === "p" && from.f !== to.f && !target) {
      board[from.r][to.f] = null;
    }
    board[to.r][to.f] = m[5]
      ? (isWhite(piece) ? m[5].toUpperCase() : m[5].toLowerCase()) // promotion
      : piece;
    board[from.r][from.f] = null;
    // castling (8x8 only): the king hops two files, the rook follows
    if (piece.toLowerCase() === "k" && Math.abs(to.f - from.f) === 2 && files === 8) {
      const kingside = to.f > from.f;
      const rookFrom = kingside ? 7 : 0;
      const rookTo = kingside ? to.f - 1 : to.f + 1;
      const rook = board[from.r][rookFrom];
      if (rook && rook.toLowerCase() === "r") {
        board[from.r][rookTo] = rook;
        board[from.r][rookFrom] = null;
      }
    }
    plays.push({ from, to, idx });
    whiteToMove = !whiteToMove;
  });

  return { board, plays, ghosts, residue };
}
