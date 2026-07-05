"""
engine_client.py -- thin UCI-over-subprocess wrapper around Fairy-Stockfish,
shared by data/selfplay.py (corpus generation) and harness.py (the
verification/play harness). This is the single place that knows how to talk
to the engine, so the legality-check primitive is genuinely the same code in
both places rather than two implementations that could drift apart.
"""
from __future__ import annotations

import subprocess


class Engine:
    def __init__(self, variant: str, variants_ini: str = "", skill_level: int = None):
        self.proc = subprocess.Popen(
            ["fairy-stockfish"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        self._send("uci")
        self._wait_for("uciok")
        if variants_ini:
            self._send(f"load {variants_ini}")
        self._send(f"setoption name UCI_Variant value {variant}")
        if skill_level is not None:
            self._send(f"setoption name Skill Level value {skill_level}")
        self._send("isready")
        self._wait_for("readyok")

    def _send(self, cmd: str):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def _wait_for(self, token: str):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"engine exited before '{token}'")
            if token in line:
                return line

    def _set_position(self, moves: list):
        self._send("position startpos" + (" moves " + " ".join(moves) if moves else ""))

    def legal_moves(self, moves: list) -> list:
        """Legal moves in the position reached after `moves`, via `go perft 1`.
        This is the single legality-check primitive: a candidate move is
        legal iff it's in this list."""
        self._set_position(moves)
        self._send("go perft 1")
        legal = []
        while True:
            line = self.proc.stdout.readline()
            if not line or line.startswith("Nodes searched"):
                break
            line = line.strip()
            if ":" in line:
                legal.append(line.split(":")[0])
        return legal

    def evaluate(self, moves: list, depth: int = 10) -> dict:
        """Engine score of the position after `moves`, from the side-to-move's
        perspective: {'kind': 'cp'|'mate', 'value': int}. Used by Token Chess
        round three to adjudicate games that end by budget exhaustion."""
        self._set_position(moves)
        self._send(f"go depth {depth}")
        kind, value = "cp", 0
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("engine exited during evaluate")
            if " score cp " in line:
                kind, value = "cp", int(line.split(" score cp ")[1].split()[0])
            elif " score mate " in line:
                kind, value = "mate", int(line.split(" score mate ")[1].split()[0])
            if line.startswith("bestmove"):
                return {"kind": kind, "value": value}

    def best_move(self, moves: list, depth: int = 6) -> str:
        """The engine's own choice, used when the engine itself is a player
        (self-play corpus generation, or the harness's opponent side)."""
        self._set_position(moves)
        self._send(f"go depth {depth}")
        line = self._wait_for("bestmove")
        move = line.split()[1]
        return None if move in ("(none)", "0000") else move

    def close(self):
        try:
            self._send("quit")
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
