#!/usr/bin/env python3
"""
TETRIS — Vintage Soviet Edition
Green phosphor CRT aesthetic, ASCII borders (!  !)
Keyboard: ← → ↑  soft-drop ↓  hard-drop Space  pause P
Touch:    on-screen buttons at bottom
"""

import pygame
import random
import sys
import math
import argparse

pygame.init()

# ─────────────────────────────────────────────────────
#  PALETTE  (phosphor green CRT)
# ─────────────────────────────────────────────────────
C_BG        = (  0,   6,   0)
C_SCANLINE  = (  0,   0,   0)   # drawn semi-transparent
C_GRID_DOT  = (  0,  30,   8)
C_BORDER    = (  0, 210,  55)
C_CELL      = (  0, 160,  38)
C_CELL_HI   = ( 55, 255,  85)
C_CELL_SH   = (  0,  70,  18)
C_GHOST     = (  0,  50,  14)
C_TEXT      = (  0, 230,  60)
C_DIMTEXT   = (  0, 100,  28)
C_BRIGHT    = (160, 255, 160)
C_BTN_N     = (  0,  32,   8)
C_BTN_H     = (  0,  75,  22)
C_BTN_P     = (  0, 180,  48)
C_BTN_BD    = (  0, 160,  40)

# ─────────────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────────────
COLS, ROWS = 10, 20
CELL       = 26          # px per cell

BOARD_W = COLS * CELL    # 260
BOARD_H = ROWS * CELL    # 520
PANEL_W = 130
PAD     = 18
TOUCH_H = 168            # touch control strip height

WIN_W = PAD + BOARD_W + PAD + PANEL_W + PAD    # 454
WIN_H = PAD + BOARD_H + PAD + TOUCH_H          # 724

BX = PAD     # board left
BY = PAD     # board top
PX = BX + BOARD_W + PAD    # panel left

# ─────────────────────────────────────────────────────
#  TETROMINOES
# ─────────────────────────────────────────────────────
SHAPES = {
    'I': [[1, 1, 1, 1]],
    'O': [[1, 1],
          [1, 1]],
    'T': [[0, 1, 0],
          [1, 1, 1]],
    'S': [[0, 1, 1],
          [1, 1, 0]],
    'Z': [[1, 1, 0],
          [0, 1, 1]],
    'J': [[1, 0, 0],
          [1, 1, 1]],
    'L': [[0, 0, 1],
          [1, 1, 1]],
}

LINE_PTS = {1: 100, 2: 300, 3: 500, 4: 800}

def fall_ms(level):
    return max(80, 800 - (level - 1) * 72)


# ─────────────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────────────
def _rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]


class Piece:
    def __init__(self, name=None):
        self.name  = name or random.choice(list(SHAPES))
        self.shape = [r[:] for r in SHAPES[self.name]]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def cells(self):
        return [
            (self.x + c, self.y + r)
            for r, row in enumerate(self.shape)
            for c, v in enumerate(row) if v
        ]

    def rotated(self):
        p      = Piece(self.name)
        p.shape = _rotate(self.shape)
        p.x, p.y = self.x, self.y
        return p

    def copy(self):
        p = Piece(self.name)
        p.shape = [r[:] for r in self.shape]
        p.x, p.y = self.x, self.y
        return p


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board   = [[0] * COLS for _ in range(ROWS)]
        self.score   = 0
        self.lines   = 0
        self.level   = 1
        self.over    = False
        self.paused  = False
        self.current = Piece()
        self.next    = Piece()
        self._fall_t = pygame.time.get_ticks()
        self._flash  = []      # [(row, timer)] rows flashing before clear
        self._flash_dur = 120  # ms

    # ── collision ──────────────────────────────────────
    def _valid(self, piece):
        for x, y in piece.cells():
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.board[y][x]:
                return False
        return True

    # ── locking ────────────────────────────────────────
    def _lock(self):
        for x, y in self.current.cells():
            if y < 0:
                self.over = True
                return
            self.board[y][x] = 1
        full = [r for r in range(ROWS) if all(self.board[r])]
        if full:
            self._flash = [(r, pygame.time.get_ticks()) for r in full]
        else:
            self._spawn_next()

    def _spawn_next(self):
        self.current = self.next
        self.next    = Piece()
        if not self._valid(self.current):
            self.over = True

    def _clear_pending(self):
        """Called after flash animation ends."""
        rows = [r for r, _ in self._flash]
        for r in sorted(rows, reverse=True):
            del self.board[r]
            self.board.insert(0, [0] * COLS)
        n = len(rows)
        self.lines += n
        self.score += LINE_PTS.get(n, 0) * self.level
        self.level  = 1 + self.lines // 10
        self._flash = []
        self._spawn_next()

    # ── actions ────────────────────────────────────────
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
            self._fall_t = pygame.time.get_ticks()
            return True
        self._lock()
        return False

    def hard_drop(self):
        while True:
            p = self.current.copy()
            p.y += 1
            if self._valid(p):
                self.current = p
            else:
                self._lock()
                self._fall_t = pygame.time.get_ticks()
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

    # ── tick ───────────────────────────────────────────
    def update(self, now):
        if self.over or self.paused:
            return
        # flash → clear
        if self._flash:
            if now - self._flash[0][1] >= self._flash_dur:
                self._clear_pending()
            return
        if now - self._fall_t >= fall_ms(self.level):
            self._fall_t = now
            p = self.current.copy()
            p.y += 1
            if self._valid(p):
                self.current = p
            else:
                self._lock()


# ─────────────────────────────────────────────────────
#  TOUCH BUTTON LAYOUT
# ─────────────────────────────────────────────────────
def make_buttons():
    ty  = PAD + BOARD_H + PAD + 8
    bw  = 58
    bh  = 58
    gap = 10
    cx  = WIN_W // 2

    return {
        'rotate': pygame.Rect(cx - bw // 2,          ty,             bw, bh),
        'drop':   pygame.Rect(WIN_W - PAD - bw,       ty,             bw, bh),
        'left':   pygame.Rect(cx - bw - gap - bw,     ty + bh + gap,  bw, bh),
        'down':   pygame.Rect(cx - bw // 2,           ty + bh + gap,  bw, bh),
        'right':  pygame.Rect(cx + gap,                ty + bh + gap,  bw, bh),
        'pause':  pygame.Rect(PAD,                     ty,             bw, bh),
    }


# ─────────────────────────────────────────────────────
#  STATIC SURFACES (built once)
# ─────────────────────────────────────────────────────
def _make_scanlines(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 2):
        pygame.draw.line(s, (0, 0, 0, 38), (0, y), (w, y))
    return s


def _make_vignette(w, h):
    s  = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    mx = math.hypot(cx, cy)
    for step in range(80):
        t     = step / 80
        r     = int(mx * (1 - t))
        alpha = int(120 * t * t)
        pygame.draw.circle(s, (0, 0, 0, alpha), (cx, cy), r, max(1, r // 10))
    return s


def _make_glow_cell(sz):
    """Single cell with phosphor glow as surface."""
    s = pygame.Surface((sz, sz), pygame.SRCALPHA)
    # outer glow
    for i in range(4, 0, -1):
        a = 20 * i
        pygame.draw.rect(s, (0, 200, 50, a),
                         pygame.Rect(i, i, sz - i * 2, sz - i * 2))
    # fill
    pygame.draw.rect(s, (*C_CELL, 255),
                     pygame.Rect(2, 2, sz - 4, sz - 4))
    # top-left highlight
    hs = max(3, sz // 4)
    pygame.draw.rect(s, (*C_CELL_HI, 200),
                     pygame.Rect(3, 3, hs, hs))
    # right/bottom shadow
    pygame.draw.line(s, C_CELL_SH, (sz - 3, 2), (sz - 3, sz - 3))
    pygame.draw.line(s, C_CELL_SH, (2, sz - 3), (sz - 3, sz - 3))
    return s


# ─────────────────────────────────────────────────────
#  RENDERER
# ─────────────────────────────────────────────────────
class Renderer:
    def __init__(self, surf):
        self.surf      = surf
        self.scanlines = _make_scanlines(WIN_W, WIN_H)
        self.vignette  = _make_vignette(WIN_W, WIN_H)
        self.cell_surf = _make_glow_cell(CELL)
        self.ghost_surf = self._make_ghost_cell(CELL)

        # fonts
        self.font  = self._mono(18)
        self.large = self._mono(22)
        self.small = self._mono(13)

        # pre-render title
        self._title = self.large.render("TETRIS", True, C_BRIGHT)

        # flicker phase
        self._t0 = pygame.time.get_ticks()

    def _mono(self, size):
        for name in ["Courier New", "Courier", "DejaVu Sans Mono",
                     "Liberation Mono", "monospace"]:
            f = pygame.font.SysFont(name, size, bold=True)
            if f:
                return f
        return pygame.font.Font(None, size + 4)

    def _make_ghost_cell(self, sz):
        s = pygame.Surface((sz, sz), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 120, 30, 60),
                         pygame.Rect(2, 2, sz - 4, sz - 4))
        pygame.draw.rect(s, (0, 160, 40, 100),
                         pygame.Rect(2, 2, sz - 4, sz - 4), 1)
        return s

    # ── board ──────────────────────────────────────────
    def draw_board(self, game):
        now = pygame.time.get_ticks()

        # fill
        pygame.draw.rect(self.surf, C_BG,
                         pygame.Rect(BX, BY, BOARD_W, BOARD_H))

        # dot grid
        for r in range(ROWS):
            for c in range(COLS):
                px = BX + c * CELL + CELL // 2
                py = BY + r * CELL + CELL // 2
                pygame.draw.circle(self.surf, C_GRID_DOT, (px, py), 1)

        # locked cells
        flash_rows = {r for r, _ in game._flash}
        for r in range(ROWS):
            for c in range(COLS):
                if game.board[r][c]:
                    if r in flash_rows:
                        # blinking white flash
                        phase = (now // 40) % 2
                        col = C_BRIGHT if phase else C_CELL
                        pygame.draw.rect(
                            self.surf, col,
                            pygame.Rect(BX + c * CELL + 1, BY + r * CELL + 1,
                                        CELL - 2, CELL - 2))
                    else:
                        self.surf.blit(self.cell_surf,
                                       (BX + c * CELL, BY + r * CELL))

        # ghost
        if not game._flash:
            for gx, gy in game.ghost().cells():
                if gy >= 0:
                    self.surf.blit(self.ghost_surf,
                                   (BX + gx * CELL, BY + gy * CELL))

        # current piece
        if not game._flash:
            for cx, cy in game.current.cells():
                if cy >= 0:
                    self.surf.blit(self.cell_surf,
                                   (BX + cx * CELL, BY + cy * CELL))

        self._draw_ascii_border()

    def _draw_ascii_border(self):
        # side rows:  (!  !)
        for r in range(ROWS):
            y = BY + r * CELL + CELL // 2 - 6
            tl = self.small.render("(!", True, C_BORDER)
            tr = self.small.render("!)", True, C_BORDER)
            self.surf.blit(tl, (BX - 14, y))
            self.surf.blit(tr, (BX + BOARD_W + 2, y))
        # top bar
        bar = "(!=" + "=" * (COLS * 2 + 1) + "=!)"
        tb  = self.small.render(bar, True, C_BORDER)
        self.surf.blit(tb, (BX - 14, BY - 14))
        # bottom bar  + zigzag
        self.surf.blit(tb, (BX - 14, BY + BOARD_H + 2))
        zz = "  " + "".join("/\\" if i % 2 == 0 else "" for i in range(COLS)) + "vvvvv"
        # classic tetris bottom decoration
        zz2 = "  " + "VVVVVVVVVV"
        tz  = self.small.render(zz2, True, C_BORDER)
        self.surf.blit(tz, (BX - 14, BY + BOARD_H + 16))

    # ── side panel ─────────────────────────────────────
    def draw_panel(self, game):
        now = pygame.time.get_ticks()
        x, y = PX, BY

        # title with phosphor flicker
        alpha = 200 + int(55 * math.sin((now - self._t0) * 0.002))
        t = self.large.render("TETRIS", True,
                              tuple(min(255, int(c * alpha / 255))
                                    for c in C_BRIGHT))
        self.surf.blit(t, (x, y - PAD))

        y += 20
        # divider
        pygame.draw.line(self.surf, C_DIMTEXT, (x, y), (x + PANEL_W - PAD, y))
        y += 8

        # NEXT label
        self.surf.blit(self.small.render("NEXT", True, C_DIMTEXT), (x, y))
        y += 16

        # next piece preview  (3×4 grid, cells = CELL-6)
        ns = CELL - 6
        pshape = game.next.shape
        pw = len(pshape[0]) * ns
        ph = len(pshape)    * ns
        ox = x + (PANEL_W - PAD - pw) // 2
        for r, row in enumerate(pshape):
            for c, v in enumerate(row):
                if v:
                    cs = _make_glow_cell(ns)
                    self.surf.blit(cs, (ox + c * ns, y + r * ns))
        y += 5 * ns + 8

        # divider
        pygame.draw.line(self.surf, C_DIMTEXT, (x, y), (x + PANEL_W - PAD, y))
        y += 10

        # stats
        for label, val in [("SCORE", f"{game.score:06d}"),
                            ("LINES", f"{game.lines:04d}"),
                            ("LEVEL", f"{game.level:02d}")]:
            self.surf.blit(self.small.render(label, True, C_DIMTEXT), (x, y))
            y += 15
            self.surf.blit(self.font.render(val, True, C_TEXT), (x, y))
            y += 26

        # divider
        pygame.draw.line(self.surf, C_DIMTEXT, (x, y), (x + PANEL_W - PAD, y))
        y += 10

        # controls legend
        for line in ["↑  ROTATE", "←→ MOVE", "↓  SOFT", "SPC DROP", "P  PAUSE"]:
            self.surf.blit(self.small.render(line, True, C_DIMTEXT), (x, y))
            y += 14

    # ── touch buttons ──────────────────────────────────
    def draw_buttons(self, buttons, pressed):
        labels = {
            'rotate': "ROT",
            'left':   " < ",
            'right':  " > ",
            'down':   " v ",
            'drop':   "|||",
            'pause':  "| |",
        }
        for name, rect in buttons.items():
            is_pressed = name in pressed
            bg  = C_BTN_P if is_pressed else C_BTN_H
            bdr = C_BORDER if is_pressed else C_BTN_BD
            pygame.draw.rect(self.surf, bg, rect, border_radius=10)
            pygame.draw.rect(self.surf, bdr, rect, 2, border_radius=10)
            lbl = labels.get(name, name[:3])
            t   = self.font.render(lbl, True, C_TEXT if is_pressed else C_DIMTEXT)
            tr  = t.get_rect(center=rect.center)
            self.surf.blit(t, tr)

    # ── overlays ───────────────────────────────────────
    def draw_overlay(self, game):
        if game.over:
            self._overlay(["GAME  OVER",
                           f"SCORE {game.score:06d}",
                           "",
                           "ENTER / TAP",
                           " TO RESTART"])
        elif game.paused:
            self._overlay(["- PAUSED -", "", "P = RESUME"])

    def _overlay(self, lines):
        s = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 170))
        self.surf.blit(s, (BX, BY))
        now = pygame.time.get_ticks()
        y0  = BY + BOARD_H // 2 - len(lines) * 17
        for i, line in enumerate(lines):
            if line == "":
                continue
            blink = i == 0 and (now // 500) % 2 == 0
            col   = C_BRIGHT if blink else C_TEXT
            t     = self.large.render(line, True, col)
            tr    = t.get_rect(centerx=BX + BOARD_W // 2, y=y0 + i * 34)
            self.surf.blit(t, tr)

    # ── CRT post-process ───────────────────────────────
    def apply_crt(self):
        self.surf.blit(self.scanlines, (0, 0))
        self.surf.blit(self.vignette,  (0, 0))

    # ── full frame ─────────────────────────────────────
    def frame(self, game, buttons, pressed):
        self.surf.fill(C_BG)
        self.draw_board(game)
        self.draw_panel(game)
        self.draw_buttons(buttons, pressed)
        self.draw_overlay(game)
        self.apply_crt()


# ─────────────────────────────────────────────────────
#  KEY REPEAT HELPER
# ─────────────────────────────────────────────────────
class KeyRepeat:
    """Fires action at held-key intervals without blocking."""
    DELAY    = 160   # ms before first repeat
    INTERVAL =  55   # ms between repeats

    def __init__(self):
        self._held = {}    # key → (press_time, last_fire_time)

    def press(self, key, now):
        self._held[key] = (now, now)

    def release(self, key):
        self._held.pop(key, None)

    def fires(self, key, now):
        """Returns True if the held key should fire an action this frame."""
        if key not in self._held:
            return False
        t0, last = self._held[key]
        elapsed = now - t0
        if elapsed < self.DELAY:
            return False
        if now - last >= self.INTERVAL:
            self._held[key] = (t0, now)
            return True
        return False


# ─────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Vintage Tetris")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="Scale factor (e.g. 2 for 2x, useful on mobile/Termux:X11)")
    args = ap.parse_args()
    scale = max(0.5, min(4.0, args.scale))

    # Internal surface always at native resolution; screen scales it up
    canvas = pygame.Surface((WIN_W, WIN_H))
    screen = pygame.display.set_mode(
        (int(WIN_W * scale), int(WIN_H * scale)),
        pygame.RESIZABLE,
    )
    pygame.display.set_caption("TETRIS — Vintage Edition")
    pygame.key.set_repeat(0)   # we handle repeat ourselves

    game     = Game()
    renderer = Renderer(canvas)
    buttons  = make_buttons()
    pressed  = set()          # currently pressed touch buttons
    kr       = KeyRepeat()
    clock    = pygame.time.Clock()

    # touch finger tracking: finger_id → button name
    finger_map = {}

    def _to_canvas(pos):
        """Map screen coordinates → canvas coordinates."""
        sw, sh = screen.get_size()
        return (int(pos[0] * WIN_W / sw), int(pos[1] * WIN_H / sh))

    def _btn_hit(pos):
        for name, rect in buttons.items():
            if rect.collidepoint(pos):
                return name
        return None

    def _do_action(name):
        if game.over:
            game.reset()
            return
        if name == 'pause':
            game.paused = not game.paused
            return
        if game.paused:
            return
        if name == 'rotate': game.rotate()
        elif name == 'left':  game.move(-1)
        elif name == 'right': game.move(1)
        elif name == 'down':  game.soft_drop()
        elif name == 'drop':  game.hard_drop()

    running = True
    while running:
        now = pygame.time.get_ticks()

        # ── events ─────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            # ── keyboard ──
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE) and game.over:
                    game.reset()
                elif ev.key == pygame.K_p:
                    game.paused = not game.paused
                elif not game.paused and not game.over:
                    if ev.key == pygame.K_LEFT:
                        game.move(-1);  kr.press(pygame.K_LEFT, now)
                    elif ev.key == pygame.K_RIGHT:
                        game.move(1);   kr.press(pygame.K_RIGHT, now)
                    elif ev.key == pygame.K_DOWN:
                        game.soft_drop(); kr.press(pygame.K_DOWN, now)
                    elif ev.key in (pygame.K_UP, pygame.K_x, pygame.K_z):
                        game.rotate()
                    elif ev.key == pygame.K_SPACE:
                        game.hard_drop()

            elif ev.type == pygame.KEYUP:
                kr.release(ev.key)

            # ── mouse (desktop touch simulation) ──
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                name = _btn_hit(_to_canvas(ev.pos))
                if name:
                    pressed.add(name)
                    _do_action(name)
                elif game.over:
                    game.reset()

            elif ev.type == pygame.MOUSEBUTTONUP:
                pressed.clear()

            # ── real touch ──
            elif ev.type == pygame.FINGERDOWN:
                sw, sh = screen.get_size()
                px = int(ev.x * sw * WIN_W / sw)
                py = int(ev.y * sh * WIN_H / sh)
                name = _btn_hit((int(ev.x * WIN_W), int(ev.y * WIN_H)))
                if name:
                    finger_map[ev.finger_id] = name
                    pressed.add(name)
                    _do_action(name)
                elif game.over:
                    game.reset()

            elif ev.type == pygame.FINGERUP:
                name = finger_map.pop(ev.finger_id, None)
                if name:
                    pressed.discard(name)

        # ── key repeat ─────────────────────────────────
        if not game.paused and not game.over:
            if kr.fires(pygame.K_LEFT,  now): game.move(-1)
            if kr.fires(pygame.K_RIGHT, now): game.move(1)
            if kr.fires(pygame.K_DOWN,  now): game.soft_drop()

        # ── update logic ───────────────────────────────
        game.update(now)

        # ── draw ───────────────────────────────────────
        renderer.frame(game, buttons, pressed)
        if scale == 1.0:
            screen.blit(canvas, (0, 0))
        else:
            pygame.transform.scale(canvas, screen.get_size(), screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
