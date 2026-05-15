#!/usr/bin/env python3
"""
TETRIS — Terminal Edition  (full-screen 9:16)
Pure Python curses, zero dependencies.
Fills the entire terminal — cells scale to terminal height.
Works natively in Termux — no X11, no pip install.

Controls: ← → move | ↑/x rotate | ↓ soft drop | Space hard drop | p pause | q quit
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
    return max(0.06, 0.8 - (level - 1) * 0.07)

SHAPES = {
    'I': [[1, 1, 1, 1]],
    'O': [[1, 1], [1, 1]],
    'T': [[0, 1, 0], [1, 1, 1]],
    'S': [[0, 1, 1], [1, 1, 0]],
    'Z': [[1, 1, 0], [0, 1, 1]],
    'J': [[1, 0, 0], [1, 1, 1]],
    'L': [[0, 0, 1], [1, 1, 1]],
}

def _rot(s):
    return [list(r) for r in zip(*s[::-1])]


# ─────────────────────────────────────────────────────
#  PIECE & GAME
# ─────────────────────────────────────────────────────
class Piece:
    def __init__(self, name=None):
        self.name  = name or random.choice(list(SHAPES))
        self.shape = [r[:] for r in SHAPES[self.name]]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def cells(self):
        return [(self.x + c, self.y + r)
                for r, row in enumerate(self.shape)
                for c, v in enumerate(row) if v]

    def rotated(self):
        p = Piece(self.name); p.shape = _rot(self.shape)
        p.x, p.y = self.x, self.y; return p

    def copy(self):
        p = Piece(self.name); p.shape = [r[:] for r in self.shape]
        p.x, p.y = self.x, self.y; return p


class Game:
    def __init__(self): self.reset()

    def reset(self):
        self.board    = [[0] * COLS for _ in range(ROWS)]
        self.score    = 0; self.lines = 0; self.level = 1
        self.over     = False; self.paused = False
        self.current  = Piece(); self.next = Piece()
        self._fall_t  = time.time()
        self._flash   = []; self._flash_t = 0.0

    def _valid(self, p):
        for x, y in p.cells():
            if x < 0 or x >= COLS or y >= ROWS: return False
            if y >= 0 and self.board[y][x]:      return False
        return True

    def _lock(self):
        for x, y in self.current.cells():
            if y < 0: self.over = True; return
            self.board[y][x] = 1
        full = [r for r in range(ROWS) if all(self.board[r])]
        if full: self._flash = full; self._flash_t = time.time()
        else:    self._spawn()

    def _spawn(self):
        self.current = self.next; self.next = Piece()
        if not self._valid(self.current): self.over = True

    def _clear(self):
        n = len(self._flash)
        for r in sorted(self._flash, reverse=True):
            del self.board[r]; self.board.insert(0, [0] * COLS)
        self.lines += n
        self.score += LINE_PTS.get(n, 0) * self.level
        self.level  = 1 + self.lines // 10
        self._flash = []; self._spawn()

    def move(self, dx):
        p = self.current.copy(); p.x += dx
        if self._valid(p): self.current = p

    def rotate(self):
        r = self.current.rotated()
        for k in [0, 1, -1, 2, -2]:
            r.x = self.current.x + k
            if self._valid(r): self.current = r; return

    def soft_drop(self):
        p = self.current.copy(); p.y += 1
        if self._valid(p): self.current = p; self._fall_t = time.time()
        else: self._lock()

    def hard_drop(self):
        while True:
            p = self.current.copy(); p.y += 1
            if self._valid(p): self.current = p
            else: self._lock(); self._fall_t = time.time(); break

    def ghost(self):
        g = self.current.copy()
        while True:
            g2 = g.copy(); g2.y += 1
            if self._valid(g2): g = g2
            else: return g

    def update(self):
        if self.over or self.paused: return
        if self._flash:
            if time.time() - self._flash_t > 0.12: self._clear()
            return
        now = time.time()
        if now - self._fall_t >= fall_sec(self.level):
            self._fall_t = now; p = self.current.copy(); p.y += 1
            if self._valid(p): self.current = p
            else: self._lock()


# ─────────────────────────────────────────────────────
#  LAYOUT  (dynamic, fills the screen)
# ─────────────────────────────────────────────────────
MIN_PANEL = 14   # min panel width to keep side panel

def compute_layout(H, W):
    """
    Find the largest square cells that fit in the terminal,
    keeping at least MIN_PANEL cols for the side panel.

    Returns dict with:
      cell_h, cell_w  : cell dimensions in terminal chars
      bx, by          : board top-left (first cell position)
      board_px        : screen col of left border "(!..."
      board_w         : total board char width incl. borders
      board_h         : total board char height incl. borders
      panel_x         : panel start column
      panel_w         : panel width
    """
    best = None
    for ch in range(5, 0, -1):
        cw = ch * 2                     # 2:1 ratio → visually square
        bw = COLS * cw + 4              # "(!" + cells + "!)"
        bh = ROWS * ch + 2             # top bar + cells + bot bar
        # Check fits: board height ≤ H-1 (leave 1 row for VVVV/deco)
        # board + panel ≤ W
        if bh <= H - 1 and bw + MIN_PANEL <= W:
            best = (ch, cw, bw, bh)
            break

    if best is None:
        # Minimal fallback: cell 1×2
        ch, cw = 1, 2
        bw = COLS * cw + 4
        bh = ROWS * ch + 2
        best = (ch, cw, bw, bh)

    ch, cw, bw, bh = best

    # Board cells start at col 2 (after "(!"), row 0
    bx = 2
    by = 0

    # Panel
    px = bw + 2
    pw = W - px

    return {
        'cell_h': ch, 'cell_w': cw,
        'bx': bx,     'by': by,
        'board_px': 0, 'board_w': bw, 'board_h': bh,
        'panel_x': px, 'panel_w': pw,
    }


# ─────────────────────────────────────────────────────
#  CELL RENDERING
# ─────────────────────────────────────────────────────
def cell_row_str(kind, cw, row_in_cell, cell_h, blink):
    """One terminal row of a cell (cw chars wide)."""
    if kind == 'filled':
        if cell_h == 1:
            return '[' + '=' * max(0, cw - 2) + ']'
        if row_in_cell == 0:
            return '/' + '-' * max(0, cw - 2) + '\\'
        if row_in_cell == cell_h - 1:
            return '\\' + '-' * max(0, cw - 2) + '/'
        return '|' + ' ' * max(0, cw - 2) + '|'
    if kind == 'ghost':
        return ':' * cw
    if kind == 'empty':
        return ('. ' * (cw // 2))[:cw] if row_in_cell == 0 else ' ' * cw
    if kind == 'flash':
        return ('##' * (cw // 2 + 1))[:cw] if blink else ' ' * cw
    return ' ' * cw


# ─────────────────────────────────────────────────────
#  COLOR PAIRS
# ─────────────────────────────────────────────────────
CP_CELL  = 1   # green bold — filled cells
CP_DIM   = 2   # dim green  — dots, border, labels
CP_BRIGHT= 3   # white bold — title, values
CP_GHOST = 4   # dark green — ghost piece outline
CP_FLASH = 5   # black on green — line-clear blink

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(CP_CELL,  curses.COLOR_GREEN, -1)
    curses.init_pair(CP_DIM,   curses.COLOR_GREEN, -1)
    curses.init_pair(CP_BRIGHT,curses.COLOR_WHITE, -1)
    curses.init_pair(CP_GHOST, curses.COLOR_GREEN, -1)
    curses.init_pair(CP_FLASH, curses.COLOR_BLACK, curses.COLOR_GREEN)


# ─────────────────────────────────────────────────────
#  DRAW
# ─────────────────────────────────────────────────────
def _p(scr, y, x, s, at, H, W):
    """Safe addstr clipped to terminal."""
    if y < 0 or y >= H - 1 or x >= W or x < 0: return
    s = s[:max(0, W - x)]
    if s:
        try: scr.addstr(y, x, s, at)
        except curses.error: pass


def draw(scr, game, L, H, W):
    scr.erase()
    now = time.time()

    ch   = L['cell_h'];  cw   = L['cell_w']
    bx   = L['bx'];      by   = L['by']
    bw   = L['board_w']; bh   = L['board_h']
    px   = L['panel_x']; pw   = L['panel_w']

    blink    = int(now * 10) % 2 == 0
    flash_s  = set(game._flash)
    ghost_s  = set() if game._flash else {(x,y) for x,y in game.ghost().cells()}
    cur_s    = set() if game._flash else {(x,y) for x,y in game.current.cells()}

    G  = curses.color_pair(CP_CELL)  | curses.A_BOLD
    D  = curses.color_pair(CP_DIM)
    B  = curses.color_pair(CP_BRIGHT)| curses.A_BOLD
    GH = curses.color_pair(CP_GHOST)
    FL = curses.color_pair(CP_FLASH) | curses.A_BOLD

    # ── board cells ──────────────────────────────────
    for r in range(ROWS):
        for c in range(COLS):
            sx = bx + c * cw
            sy = by + r * ch
            if r in flash_s:       kind = 'flash'
            elif game.board[r][c]: kind = 'filled'
            elif (c, r) in cur_s:  kind = 'filled'
            elif (c, r) in ghost_s:kind = 'ghost'
            else:                   kind = 'empty'
            at = FL if kind == 'flash' else \
                 G  if kind == 'filled' else \
                 GH if kind == 'ghost'  else D
            for dh in range(ch):
                s = cell_row_str(kind, cw, dh, ch, blink)
                _p(scr, sy + dh, sx, s, at, H, W)

    # ── ASCII borders ─────────────────────────────────
    bar = '(!=' + '=' * (COLS * cw) + '=!)'
    _p(scr, by - 1,         0, bar, G, H, W)   # top bar  (row -1 → by=0 means row -1 is above)
    _p(scr, by + ROWS * ch, 0, bar, G, H, W)   # bot bar

    # actually if by=0, top bar must be at row 0 — shift board down 1
    # handled below in layout: board cells start at row 1 when by=0 means "cell row 0 = screen row 1"

    for r in range(ROWS):
        for dh in range(ch):
            sy = by + r * ch + dh
            _p(scr, sy, 0,         '(!', G, H, W)
            _p(scr, sy, bx+COLS*cw,'!)', G, H, W)

    # ── below-board fill (controls + deco) ───────────
    deco_y = by + ROWS * ch + 1   # one row after bottom bar

    vvv = ('VV' * (bw // 2))[:bw]
    _p(scr, deco_y, 0, vvv, D, H, W)

    ctrl_lines = [
        '',
        '  ←→  MOVE   ↑/x ROTATE',
        '  ↓   SOFT   SPC DROP',
        '  p  PAUSE  q   QUIT',
        '',
    ]
    ry = deco_y + 1
    ci = 0
    while ry < H - 1:
        if ci < len(ctrl_lines):
            line = ctrl_lines[ci]; ci += 1
        else:
            # decorative fill — alternating patterns
            row_idx = ry - deco_y
            if row_idx % 4 == 0:
                line = '  ' + '~ ' * (bw // 4)
            elif row_idx % 4 == 2:
                line = '  ' + '. ' * (bw // 4)
            else:
                line = ''
        _p(scr, ry, 0, line, D, H, W)
        ry += 1

    # ── side panel (fills full height) ───────────────
    if pw >= 8:
        py2 = 0

        # Phosphor-flicker title
        flicker = int(now * 1.5) % 8 == 0
        title_at = D if flicker else B
        _p(scr, py2, px, 'TETRIS', title_at, H, W); py2 += 1
        _p(scr, py2, px, '------', D, H, W);         py2 += 1

        # NEXT piece
        _p(scr, py2, px, 'NEXT', D, H, W); py2 += 1
        ph = len(game.next.shape)
        pw2 = len(game.next.shape[0])
        for r2, row in enumerate(game.next.shape):
            for c2, v in enumerate(row):
                if v:
                    for dh in range(ch):
                        s = cell_row_str('filled', cw, dh, ch, False)
                        _p(scr, py2 + r2*ch + dh, px + c2*cw, s, G, H, W)
        py2 += ph * ch + 1
        _p(scr, py2, px, '------', D, H, W); py2 += 1

        # Stats
        for label, val in [('SCORE', f'{game.score:06d}'),
                            ('LINES', f'{game.lines:04d}'),
                            ('LEVEL', f'{game.level:02d}')]:
            _p(scr, py2,     px, label, D, H, W)
            _p(scr, py2 + 1, px, val,   B, H, W)
            py2 += 3

        # Level progress bar
        _p(scr, py2, px, 'PROGRESS', D, H, W); py2 += 1
        bar_w    = pw - 2
        filled_w = (game.lines % 10) * bar_w // 10
        bar_str  = '[' + '#' * filled_w + '-' * (bar_w - filled_w) + ']'
        _p(scr, py2, px, bar_str[:pw], D, H, W); py2 += 2

        # Speed indicator
        spd = int((1.0 - fall_sec(game.level) / 0.8) * 100)
        spd = max(0, min(99, spd))
        _p(scr, py2, px, f'SPEED {spd:02d}%', D, H, W); py2 += 2

        _p(scr, py2, px, '------', D, H, W); py2 += 1

        # Controls legend in panel
        ctrl = ['←→ MOVE', '↑  ROT', '↓  SOFT',
                'SP DROP', 'p PAUSE', 'q QUIT']
        for line in ctrl:
            if py2 < H - 1:
                _p(scr, py2, px, line, D, H, W); py2 += 1

        _p(scr, py2, px, '------', D, H, W); py2 += 1

        # Fill remainder with decorative dots
        while py2 < H - 1:
            row_fill = ('. ' * (pw // 2))[:pw]
            if (py2 % 3) == 0:
                _p(scr, py2, px, row_fill, D, H, W)
            py2 += 1

    # ── overlays ──────────────────────────────────────
    if game.over:
        msgs = ['GAME OVER', f'SCORE:{game.score:06d}', '', 'ENTER=NEW']
        oy = by + (ROWS * ch) // 2 - 4
        for m in msgs:
            ox = bx + max(0, (COLS * cw - len(m)) // 2)
            _p(scr, oy, ox, m, B, H, W); oy += 2
    elif game.paused:
        m  = '- PAUSED -'
        oy = by + (ROWS * ch) // 2
        ox = bx + max(0, (COLS * cw - len(m)) // 2)
        _p(scr, oy, ox, m, B, H, W)

    try:
        scr.refresh()
    except curses.error:
        pass


# ─────────────────────────────────────────────────────
#  FIX LAYOUT  (top bar at row 0, cells start at row 1)
# ─────────────────────────────────────────────────────
def get_layout(H, W):
    L = compute_layout(H, W)
    # shift board down by 1 so top border fits at row 0
    L['by'] = 1
    return L


# ─────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────
def _run(scr):
    curses.curs_set(0)
    scr.nodelay(True)
    scr.timeout(33)      # ~30 fps
    init_colors()

    game = Game()
    H, W = scr.getmaxyx()
    L    = get_layout(H, W)

    held      = {}
    held_last = {}
    HOLD_DELAY = 0.16
    HOLD_INT   = 0.055

    while True:
        now = time.time()
        key = scr.getch()

        # Terminal resize
        if key == curses.KEY_RESIZE:
            H, W = scr.getmaxyx()
            L    = get_layout(H, W)
            scr.clear()

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
                held[curses.KEY_LEFT] = now; held_last[curses.KEY_LEFT] = now
                held.pop(curses.KEY_RIGHT, None)
            elif key == curses.KEY_RIGHT:
                game.move(1)
                held[curses.KEY_RIGHT] = now; held_last[curses.KEY_RIGHT] = now
                held.pop(curses.KEY_LEFT, None)
            elif key == curses.KEY_DOWN:
                game.soft_drop()
                held[curses.KEY_DOWN] = now; held_last[curses.KEY_DOWN] = now
            elif key in (curses.KEY_UP, ord('x'), ord('X'), ord('z'), ord('Z')):
                game.rotate()
            elif key == ord(' '):
                game.hard_drop()
            elif key == -1:
                for k in [curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_DOWN]:
                    if k in held and now - held[k] > HOLD_DELAY:
                        if now - held_last.get(k, 0) >= HOLD_INT:
                            held_last[k] = now
                            if k == curses.KEY_LEFT:   game.move(-1)
                            elif k == curses.KEY_RIGHT: game.move(1)
                            elif k == curses.KEY_DOWN:  game.soft_drop()
            else:
                held.clear(); held_last.clear()

        game.update()
        H2, W2 = scr.getmaxyx()
        if (H2, W2) != (H, W):
            H, W = H2, W2
            L = get_layout(H, W)
        draw(scr, game, L, H, W)


def main():
    try:
        curses.wrapper(_run)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
