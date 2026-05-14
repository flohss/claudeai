#!/usr/bin/env python3
"""
TETRIS — Terminal Edition
Pure Python curses, zero dependencies beyond stdlib.
Works natively in Termux — no X11, no pip install needed.

Controls:
  ← →        move
  ↑ / x / z  rotate
  ↓           soft drop
  Space       hard drop
  p           pause
  q           quit / new game on game over: Enter or Space
"""

import curses
import random
import time
import sys

# ─────────────────────────────────────────────────────
#  GAME CONSTANTS
# ─────────────────────────────────────────────────────
COLS, ROWS = 10, 20
LINE_PTS   = {1: 100, 2: 300, 3: 500, 4: 800}

def fall_sec(level):
    return max(0.08, 0.8 - (level - 1) * 0.07)

SHAPES = {
    'I': [[1, 1, 1, 1]],
    'O': [[1, 1], [1, 1]],
    'T': [[0, 1, 0], [1, 1, 1]],
    'S': [[0, 1, 1], [1, 1, 0]],
    'Z': [[1, 1, 0], [0, 1, 1]],
    'J': [[1, 0, 0], [1, 1, 1]],
    'L': [[0, 0, 1], [1, 1, 1]],
}

def _rot(shape):
    return [list(r) for r in zip(*shape[::-1])]


# ─────────────────────────────────────────────────────
#  PIECE
# ─────────────────────────────────────────────────────
class Piece:
    def __init__(self, name=None):
        self.name  = name or random.choice(list(SHAPES))
        self.shape = [r[:] for r in SHAPES[self.name]]
        self.x     = COLS // 2 - len(self.shape[0]) // 2
        self.y     = 0

    def cells(self):
        return [(self.x + c, self.y + r)
                for r, row in enumerate(self.shape)
                for c, v in enumerate(row) if v]

    def rotated(self):
        p = Piece(self.name)
        p.shape  = _rot(self.shape)
        p.x, p.y = self.x, self.y
        return p

    def copy(self):
        p = Piece(self.name)
        p.shape  = [r[:] for r in self.shape]
        p.x, p.y = self.x, self.y
        return p


# ─────────────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────────────
class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board    = [[0] * COLS for _ in range(ROWS)]
        self.score    = 0
        self.lines    = 0
        self.level    = 1
        self.over     = False
        self.paused   = False
        self.current  = Piece()
        self.next     = Piece()
        self._fall_t  = time.time()
        self._flash   = []
        self._flash_t = 0.0

    def _valid(self, p):
        for x, y in p.cells():
            if x < 0 or x >= COLS or y >= ROWS: return False
            if y >= 0 and self.board[y][x]:      return False
        return True

    def _lock(self):
        for x, y in self.current.cells():
            if y < 0:
                self.over = True
                return
            self.board[y][x] = 1
        full = [r for r in range(ROWS) if all(self.board[r])]
        if full:
            self._flash   = full
            self._flash_t = time.time()
        else:
            self._spawn()

    def _spawn(self):
        self.current = self.next
        self.next    = Piece()
        if not self._valid(self.current):
            self.over = True

    def _clear(self):
        n = len(self._flash)
        for r in sorted(self._flash, reverse=True):
            del self.board[r]
            self.board.insert(0, [0] * COLS)
        self.lines += n
        self.score += LINE_PTS.get(n, 0) * self.level
        self.level  = 1 + self.lines // 10
        self._flash = []
        self._spawn()

    def move(self, dx):
        p = self.current.copy()
        p.x += dx
        if self._valid(p):
            self.current = p

    def rotate(self):
        r = self.current.rotated()
        for kick in [0, 1, -1, 2, -2]:
            r.x = self.current.x + kick
            if self._valid(r):
                self.current = r
                return

    def soft_drop(self):
        p = self.current.copy()
        p.y += 1
        if self._valid(p):
            self.current = p
            self._fall_t = time.time()
        else:
            self._lock()

    def hard_drop(self):
        while True:
            p = self.current.copy()
            p.y += 1
            if self._valid(p):
                self.current = p
            else:
                self._lock()
                self._fall_t = time.time()
                break

    def ghost(self):
        g = self.current.copy()
        while True:
            g2 = g.copy()
            g2.y += 1
            if self._valid(g2):
                g = g2
            else:
                return g

    def update(self):
        if self.over or self.paused:
            return
        if self._flash:
            if time.time() - self._flash_t > 0.12:
                self._clear()
            return
        now = time.time()
        if now - self._fall_t >= fall_sec(self.level):
            self._fall_t = now
            p = self.current.copy()
            p.y += 1
            if self._valid(p):
                self.current = p
            else:
                self._lock()


# ─────────────────────────────────────────────────────
#  COLOR PAIRS  (phosphor green palette)
# ─────────────────────────────────────────────────────
CP_CELL   = 1   # bright green  — filled cells
CP_DIM    = 2   # dim green     — dots, borders
CP_BRIGHT = 3   # white bold    — title, values
CP_GHOST  = 4   # dark green    — ghost
CP_FLASH  = 5   # black on green — line clear flash

def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_CELL,   curses.COLOR_GREEN, -1)
    curses.init_pair(CP_DIM,    curses.COLOR_GREEN, -1)
    curses.init_pair(CP_BRIGHT, curses.COLOR_WHITE, -1)
    curses.init_pair(CP_GHOST,  curses.COLOR_GREEN, -1)
    curses.init_pair(CP_FLASH,  curses.COLOR_BLACK, curses.COLOR_GREEN)


# ─────────────────────────────────────────────────────
#  RENDERER
# ─────────────────────────────────────────────────────
# Screen layout:
#   row 0            : top border  (!====!)    title TETRIS
#   row 1..20  (BY+r): board rows  (!  ....!)
#   row 21           : bot border  (!====!)
#   row 22           : VVVVVVVVVV
#   col 0..1         : left border  (!
#   col BX..BX+19    : cells (2 chars each)
#   col BX+20..21    : right border  !)
#   col PX+          : side panel

BX = 2        # board cells start column  (after "(!")
BY = 1        # board cells start row     (after top bar)
PX = BX + COLS * 2 + 4   # panel column

def _put(scr, y, x, s, attr, maxr, maxc):
    if 0 <= y < maxr - 1 and 0 <= x and x + len(s) <= maxc:
        try:
            scr.addstr(y, x, s, attr)
        except curses.error:
            pass


def _draw(scr, game):
    scr.erase()
    maxr, maxc = scr.getmaxyx()
    now = time.time()

    flash_set  = set(game._flash)
    blink_on   = int(now * 10) % 2 == 0
    ghost_set  = set() if game._flash else {(x, y) for x, y in game.ghost().cells()}
    cur_set    = set() if game._flash else {(x, y) for x, y in game.current.cells()}

    cell_at   = curses.color_pair(CP_CELL)  | curses.A_BOLD
    dim_at    = curses.color_pair(CP_DIM)
    bright_at = curses.color_pair(CP_BRIGHT)| curses.A_BOLD
    ghost_at  = curses.color_pair(CP_GHOST)
    flash_on  = curses.color_pair(CP_FLASH) | curses.A_BOLD
    flash_off = curses.color_pair(CP_FLASH)
    border_at = curses.color_pair(CP_CELL)  | curses.A_BOLD

    # ── board cells ──────────────────────────────────
    for r in range(ROWS):
        sy = BY + r
        for c in range(COLS):
            sx = BX + c * 2
            if r in flash_set:
                ch, at = ("##", flash_on) if blink_on else ("  ", flash_off)
            elif game.board[r][c]:
                ch, at = "[]", cell_at
            elif (c, r) in cur_set:
                ch, at = "[]", cell_at
            elif (c, r) in ghost_set:
                ch, at = "::", ghost_at
            else:
                ch, at = ". ", dim_at
            _put(scr, sy, sx, ch, at, maxr, maxc)

    # ── ASCII borders ─────────────────────────────────
    bar = "(!=" + "=" * (COLS * 2) + "=!)"
    _put(scr, 0,       0, bar, border_at, maxr, maxc)
    _put(scr, BY+ROWS, 0, bar, border_at, maxr, maxc)
    _put(scr, BY+ROWS+1, 2, "VVVVVVVVVV", dim_at, maxr, maxc)

    for r in range(ROWS):
        sy = BY + r
        _put(scr, sy, 0,          "(!",  border_at, maxr, maxc)
        _put(scr, sy, BX+COLS*2,  "!)",  border_at, maxr, maxc)

    # ── side panel ────────────────────────────────────
    if PX + 8 < maxc:
        # title — subtle phosphor flicker
        title_dim = int(now * 1.5) % 7 == 0
        _put(scr, 0, PX, "TETRIS",
             curses.color_pair(CP_DIM) if title_dim else bright_at,
             maxr, maxc)

        py = 2
        _put(scr, py, PX, "NEXT", dim_at, maxr, maxc)
        py += 1
        for r2, row in enumerate(game.next.shape):
            for c2, v in enumerate(row):
                if v:
                    _put(scr, py + r2, PX + c2 * 2, "[]", cell_at, maxr, maxc)
        py += len(game.next.shape) + 2

        _put(scr, py, PX, "--------", dim_at, maxr, maxc)
        py += 1

        for label, val in [("SCORE", f"{game.score:06d}"),
                            ("LINES", f"{game.lines:04d}"),
                            ("LEVEL", f"{game.level:02d}")]:
            _put(scr, py,   PX, label, dim_at,    maxr, maxc)
            _put(scr, py+1, PX, val,   bright_at, maxr, maxc)
            py += 3

        _put(scr, py, PX, "--------", dim_at, maxr, maxc)
        py += 1
        for line in ["<> MOVE", "^  ROT", "v  SOFT",
                     "SP DROP", "p  PAUS", "q  QUIT"]:
            _put(scr, py, PX, line, dim_at, maxr, maxc)
            py += 1

    # ── overlays ──────────────────────────────────────
    if game.over:
        msgs = ["GAME OVER", f"SCORE:{game.score:06d}", "", "ENTER=NEW"]
        oy   = BY + ROWS // 2 - 3
        for m in msgs:
            ox = BX + (COLS * 2 - len(m)) // 2
            _put(scr, oy, ox, m, bright_at, maxr, maxc)
            oy += 2
    elif game.paused:
        m  = "-PAUSED-"
        oy = BY + ROWS // 2
        ox = BX + (COLS * 2 - len(m)) // 2
        _put(scr, oy, ox, m, bright_at, maxr, maxc)

    try:
        scr.refresh()
    except curses.error:
        pass


# ─────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────
def _run(scr):
    curses.curs_set(0)
    scr.nodelay(True)
    scr.timeout(40)       # ~25 fps poll
    _init_colors()

    game = Game()

    # Software key-repeat state
    held      = {}        # key → time of first press
    held_last = {}        # key → time of last fired repeat
    HOLD_DELAY = 0.16     # s before repeat starts
    HOLD_INT   = 0.055    # s between repeats

    while True:
        now = time.time()
        key = scr.getch()

        if key in (ord('q'), ord('Q')):
            break

        if game.over:
            if key in (10, 13, ord(' ')):
                game.reset()
        elif key in (ord('p'), ord('P')):
            game.paused = not game.paused
        elif not game.paused:
            if key == curses.KEY_LEFT:
                game.move(-1)
                held[curses.KEY_LEFT]      = now
                held_last[curses.KEY_LEFT] = now
                held.pop(curses.KEY_RIGHT, None)

            elif key == curses.KEY_RIGHT:
                game.move(1)
                held[curses.KEY_RIGHT]      = now
                held_last[curses.KEY_RIGHT] = now
                held.pop(curses.KEY_LEFT, None)

            elif key == curses.KEY_DOWN:
                game.soft_drop()
                held[curses.KEY_DOWN]      = now
                held_last[curses.KEY_DOWN] = now

            elif key in (curses.KEY_UP, ord('x'), ord('X'), ord('z'), ord('Z')):
                game.rotate()

            elif key == ord(' '):
                game.hard_drop()

            elif key == -1:
                # No key pressed: fire software repeat for held keys
                for k in [curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_DOWN]:
                    if k in held and now - held[k] > HOLD_DELAY:
                        if now - held_last.get(k, 0) >= HOLD_INT:
                            held_last[k] = now
                            if k == curses.KEY_LEFT:   game.move(-1)
                            elif k == curses.KEY_RIGHT: game.move(1)
                            elif k == curses.KEY_DOWN:  game.soft_drop()
            else:
                # Any other key: cancel all held
                held.clear()
                held_last.clear()

        game.update()
        _draw(scr, game)


def main():
    # Minimum terminal size check
    import shutil
    cols, rows = shutil.get_terminal_size()
    need_c = PX + 10
    need_r = BY + ROWS + 3
    if cols < need_c or rows < need_r:
        print(f"Terminal too small: need {need_c}×{need_r}, got {cols}×{rows}")
        print("Resize your terminal and retry.")
        sys.exit(1)

    try:
        curses.wrapper(_run)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
