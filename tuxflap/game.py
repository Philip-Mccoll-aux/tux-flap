# SPDX-License-Identifier: GPL-3.0-or-later
"""Tux Flap - un juego estilo Flappy Bird con el pingüino Tux y témpanos cilíndricos.

Resolución lógica vertical (360x640) escalada a cualquier pantalla, pensada
para móviles Linux (Plasma Mobile) pero jugable también con ratón o teclado.
"""
import json
import math
import os
import random
import sys

import pygame

W, H = 360, 640
GROUND_H = 84
GROUND_Y = H - GROUND_H

GRAVITY = 1500.0
FLAP_V = -430.0
MAX_FALL = 700.0
SPEED = 150.0
PIPE_W = 66
CAP_W = 82
CAP_H = 26
GAP = 168
SPACING = 215
TUX_X = 96
TUX_R = 17  # radio de colisión

APP_ID = "io.github.philip_mccoll_aux.TuxFlap"

READY, PLAYING, DEAD = range(3)


# --------------------------------------------------------------- utilidades
def _save_path():
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "tuxflap", "score.json")


def load_best():
    try:
        with open(_save_path()) as f:
            return int(json.load(f).get("best", 0))
    except Exception:
        return 0


def save_best(v):
    try:
        p = _save_path()
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            json.dump({"best": v}, f)
    except Exception:
        pass


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))


# ------------------------------------------------------------------ gráficos
def make_sky():
    s = pygame.Surface((W, H))
    top, bot = (88, 160, 214), (200, 232, 248)
    for y in range(H):
        pygame.draw.line(s, mix(top, bot, y / H), (0, y), (W, y))
    return s


def make_mountains(seed, base, amp, col, snow):
    rnd = random.Random(seed)
    width = W * 2
    s = pygame.Surface((width, 260), pygame.SRCALPHA)
    pts = [(0, 260)]
    x = 0
    while x <= width:
        h = rnd.uniform(0.35, 1.0) * amp
        pts.append((x, 260 - h))
        x += rnd.randint(50, 90)
    pts.append((width, 260))
    pts[-2] = (width, pts[1][1])  # empalme sin salto al repetir
    pygame.draw.polygon(s, col, pts)
    for px, py in pts[1:-1]:
        cap = [(px, py), (px - 16, py + 26), (px - 5, py + 20), (px + 4, py + 28), (px + 16, py + 24)]
        pygame.draw.polygon(s, snow, cap)
    return s


def make_cylinder(width, height):
    """Cilindro de hielo con degradado horizontal y brillos."""
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    dark, mid, light = (92, 168, 214), (158, 220, 245), (232, 250, 255)
    for x in range(width):
        t = x / (width - 1)
        # sombreado de cilindro: luz desde arriba-izquierda
        k = math.sin(t * math.pi)
        c = mix(dark, mid, k) if t > 0.28 else mix(mid, light, 1 - t / 0.28)
        c = mix(c, light, max(0.0, 1 - abs(t - 0.24) / 0.09) * 0.7)
        pygame.draw.line(s, c, (x, 0), (x, height))
    # vetas de hielo
    rnd = random.Random(7)
    for _ in range(height // 22):
        x = rnd.randint(8, width - 9)
        y = rnd.randint(0, height)
        pygame.draw.line(s, (255, 255, 255, 70), (x, y), (x + rnd.randint(-3, 3), y + rnd.randint(14, 40)), 1)
    return s


def make_cap(width, height):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    body = make_cylinder(width, height)
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, width, height), border_radius=9)
    s.blit(body, (0, 0))
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(s, (70, 140, 190), (0, 0, width, height), 2, border_radius=9)
    return s


def make_ground():
    s = pygame.Surface((W + 48, GROUND_H))
    s.fill((236, 246, 252))
    pygame.draw.rect(s, (205, 228, 242), (0, 10, W + 48, GROUND_H - 10))
    for x in range(0, W + 48, 24):
        pygame.draw.polygon(s, (170, 205, 228), [(x, 22), (x + 12, 22), (x + 6, 44)])
    pygame.draw.line(s, (250, 253, 255), (0, 0), (W + 48, 0), 4)
    return s


def make_tux(frame):
    """Tux dibujado con primitivas, 4x supermuestreado. frame: 0 alas arriba, 1 medio, 2 abajo."""
    S = 4
    w, h = 54, 62
    big = pygame.Surface((w * S, h * S), pygame.SRCALPHA)

    def E(color, rect):
        x, y, rw, rh = rect
        pygame.draw.ellipse(big, color, (x * S, y * S, rw * S, rh * S))

    black, white, orange = (28, 28, 34), (250, 250, 250), (250, 168, 30)
    # pies
    E(orange, (10, 52, 18, 9))
    E(orange, (26, 52, 18, 9))
    # alas (detrás del cuerpo)
    wy = {0: -6, 1: 4, 2: 14}[frame]
    for sx, sign in ((2, -1), (46, 1)):
        surf = pygame.Surface((14 * S, 30 * S), pygame.SRCALPHA)
        pygame.draw.ellipse(surf, black, (0, 0, 14 * S, 30 * S))
        ang = sign * {0: 38, 1: 8, 2: -26}[frame]
        r = pygame.transform.rotate(surf, ang)
        big.blit(r, (sx * S - (r.get_width() - 14 * S) // 2 - (6 * S if sign < 0 else 0),
                     (22 + wy) * S - (r.get_height() - 30 * S) // 2))
    # cuerpo
    E(black, (6, 4, 42, 54))
    E(white, (14, 22, 26, 33))
    # cabeza / mejillas
    E(white, (12, 11, 12, 13))
    E(white, (30, 11, 12, 13))
    E(black, (14, 8, 26, 14))
    # ojos
    for ex in (17, 29):
        E(white, (ex, 11, 9, 11))
        E(black, (ex + 4, 14, 4, 5))
    # pico
    E(orange, (17, 20, 20, 9))
    E((222, 140, 20), (20, 26, 14, 5))
    return pygame.transform.smoothscale(big, (w, h))


def make_icon_surface(size=128):
    t = make_tux(1)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 190, 232), (size // 2, size // 2), size // 2)
    t = pygame.transform.smoothscale(t, (int(54 * size / 80), int(62 * size / 80)))
    s.blit(t, ((size - t.get_width()) // 2, (size - t.get_height()) // 2))
    return s


# ------------------------------------------------------------------- sonido
def make_sounds():
    snd = {}
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        rate = pygame.mixer.get_init()[0]

        def tone(freqs, dur, vol=0.35, decay=True):
            n = int(rate * dur)
            buf = bytearray()
            for i in range(n):
                f = lerp(freqs[0], freqs[-1], i / n)
                env = (1 - i / n) if decay else 1.0
                v = int(32767 * vol * env * math.sin(2 * math.pi * f * i / rate))
                buf += v.to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(buf))

        snd["flap"] = tone((420, 760), 0.09)
        snd["score"] = tone((880, 1320), 0.14)
        snd["hit"] = tone((300, 70), 0.30, 0.5)
    except Exception:
        pass
    return snd


# ------------------------------------------------------------------- juego
class Game:
    def __init__(self, fullscreen=None):
        pygame.init()
        pygame.display.set_caption("Tux Flap")
        try:
            pygame.display.set_icon(make_icon_surface(64))
        except Exception:
            pass
        sizes = pygame.display.get_desktop_sizes()
        dw, dh = sizes[0] if sizes else (800, 600)
        if fullscreen is None:
            fullscreen = min(dw, dh) <= 900  # móvil/tablet pequeña
        self.fullscreen = fullscreen
        self.win_size = (405, 720)
        self._make_window()
        self.canvas = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()

        self.sky = make_sky()
        self.far = make_mountains(1, 0, 150, (150, 190, 220), (245, 250, 255))
        self.near = make_mountains(2, 0, 110, (112, 160, 200), (250, 253, 255))
        self.ground = make_ground()
        self.cyl = make_cylinder(PIPE_W, H)
        self.cap = make_cap(CAP_W, CAP_H)
        self.cap_flip = pygame.transform.flip(self.cap, False, True)
        self.tux = [make_tux(i) for i in range(3)]
        self.font_big = pygame.font.Font(None, 96)
        self.font_mid = pygame.font.Font(None, 44)
        self.font_sm = pygame.font.Font(None, 30)
        self.sounds = make_sounds()
        self.flakes = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.5, 1.6)] for _ in range(46)]
        self.best = load_best()
        self.running = True
        self.reset()

    # -- ventana
    def _make_window(self):
        flags = pygame.RESIZABLE
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | flags)
        else:
            self.screen = pygame.display.set_mode(self.win_size, flags)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self._make_window()

    # -- estado
    def reset(self):
        self.state = READY
        self.y = H * 0.42
        self.vy = 0.0
        self.pipes = []  # [x, gap_center, scored]
        self.score = 0
        self.t = 0.0
        self.dead_t = 0.0
        self.shake = 0.0
        self.new_best = False
        self.scroll = 0.0
        first = W + 120
        for i in range(4):
            self._add_pipe(first + i * SPACING)

    def _add_pipe(self, x):
        lo = 70 + GAP // 2
        hi = GROUND_Y - 70 - GAP // 2
        prev = self.pipes[-1][1] if self.pipes else (lo + hi) / 2
        c = min(hi, max(lo, prev + random.uniform(-190, 190)))
        self.pipes.append([x, c, False])

    def flap(self):
        if self.state == READY:
            self.state = PLAYING
        if self.state == PLAYING:
            self.vy = FLAP_V
            self._play("flap")

    def _play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()

    def die(self):
        self.state = DEAD
        self.dead_t = 0.0
        self.shake = 0.35
        self._play("hit")
        if self.score > self.best:
            self.best = self.score
            self.new_best = True
            save_best(self.best)

    # -- entrada
    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                self.running = False
            elif ev.key == pygame.K_F11:
                self.toggle_fullscreen()
            elif ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN, pygame.K_w):
                self.press()
        elif ev.type == pygame.FINGERDOWN:
            self.press()
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if getattr(ev, "touch", False):
                return  # ya contado por FINGERDOWN
            if ev.button == 1:
                self.press()

    def press(self):
        if self.state == DEAD:
            if self.dead_t > 0.55:
                self.reset()
        else:
            self.flap()

    # -- física
    def update(self, dt):
        self.t += dt
        for f in self.flakes:
            f[1] += (28 + 24 * f[2]) * dt
            f[0] += math.sin(self.t * 0.8 + f[1] * 0.02) * 12 * dt
            if f[1] > H:
                f[0], f[1] = random.uniform(0, W), -4
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)

        if self.state == DEAD:
            self.dead_t += dt
            if self.y < GROUND_Y - TUX_R:
                self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
                self.y = min(GROUND_Y - TUX_R, self.y + self.vy * dt)
            return

        self.scroll = (self.scroll + SPEED * dt) % 48
        if self.state == READY:
            self.y = H * 0.42 + math.sin(self.t * 4) * 8
            return

        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
        self.y += self.vy * dt
        for p in self.pipes:
            p[0] -= SPEED * dt
            if not p[2] and p[0] + PIPE_W / 2 < TUX_X:
                p[2] = True
                self.score += 1
                self._play("score")
        if self.pipes and self.pipes[0][0] + CAP_W / 2 < -10:
            self.pipes.pop(0)
            self._add_pipe(self.pipes[-1][0] + SPACING)

        if self.y + TUX_R >= GROUND_Y:
            self.y = GROUND_Y - TUX_R
            self.die()
            return
        if self.y - TUX_R <= 0:
            self.y = TUX_R
            self.vy = max(self.vy, 0)
        if self._hits_pipe():
            self.die()

    def _hits_pipe(self):
        for x, c, _ in self.pipes:
            top_end, bot_start = c - GAP / 2, c + GAP / 2
            for w, rects in ((PIPE_W, ((0, top_end - CAP_H), (bot_start + CAP_H, GROUND_Y))),
                             (CAP_W, ((top_end - CAP_H, top_end), (bot_start, bot_start + CAP_H)))):
                for y0, y1 in rects:
                    rx0, rx1 = x - w / 2, x + w / 2
                    nx = min(max(TUX_X, rx0), rx1)
                    ny = min(max(self.y, y0), y1)
                    if (nx - TUX_X) ** 2 + (ny - self.y) ** 2 < TUX_R ** 2:
                        return True
        return False

    # -- dibujo
    def text(self, surf, s, font, pos, color=(255, 255, 255), center=True):
        sh = font.render(s, True, (20, 50, 80))
        im = font.render(s, True, color)
        r = im.get_rect(center=pos) if center else im.get_rect(topleft=pos)
        surf.blit(sh, r.move(2, 3))
        surf.blit(im, r)

    def draw(self):
        c = self.canvas
        c.blit(self.sky, (0, 0))
        off_far = -(self.t * 6) % (W * 2) if self.state != DEAD else -(self.t * 6) % (W * 2)
        for img, speed, y in ((self.far, 6, GROUND_Y - 250), (self.near, 18, GROUND_Y - 235)):
            ox = -((self.t * speed) % W) if self.state != DEAD else -((self.t * speed) % W)
            c.blit(img, (ox, y))
            c.blit(img, (ox + img.get_width(), y))

        for x, cy, _ in self.pipes:
            top_end, bot_start = cy - GAP / 2, cy + GAP / 2
            c.blit(self.cyl, (x - PIPE_W / 2, 0), (0, H - max(0, top_end - CAP_H), PIPE_W, max(0, top_end - CAP_H)))
            c.blit(self.cap_flip, (x - CAP_W / 2, top_end - CAP_H))
            c.blit(self.cap, (x - CAP_W / 2, bot_start))
            c.blit(self.cyl, (x - PIPE_W / 2, bot_start + CAP_H), (0, 0, PIPE_W, GROUND_Y - bot_start - CAP_H))
            # punta de carámbano colgante en el cap superior
            pygame.draw.polygon(c, (170, 226, 247), [(x - 14, top_end), (x + 14, top_end), (x, top_end + 20)])
            pygame.draw.polygon(c, (110, 180, 220), [(x - 14, top_end), (x + 14, top_end), (x, top_end + 20)], 2)

        gx = -self.scroll
        c.blit(self.ground, (gx, GROUND_Y))

        # Tux
        frame = 1
        if self.state != DEAD:
            frame = (0, 1, 2, 1)[int(self.t * 12) % 4] if (self.vy < 120 or self.state == READY) else 2
        ang = max(-28, min(70, self.vy * 0.09)) if self.state != READY else 0
        img = pygame.transform.rotozoom(self.tux[frame], -ang, 1.0)
        c.blit(img, img.get_rect(center=(TUX_X, self.y)))

        for fx, fy, sz in self.flakes:
            pygame.draw.circle(c, (255, 255, 255), (int(fx), int(fy)), 1 + int(sz > 1.1))

        # HUD
        if self.state == PLAYING:
            self.text(c, str(self.score), self.font_big, (W // 2, 70))
        elif self.state == READY:
            self.text(c, "Tux Flap", self.font_big, (W // 2, 130))
            self.text(c, "Toca para aletear", self.font_mid, (W // 2, 210))
            self.text(c, f"Récord: {self.best}", self.font_sm, (W // 2, GROUND_Y + 40))
        else:
            self._draw_gameover(c)

        out = c
        if self.shake > 0:
            out = pygame.Surface((W, H))
            m = int(self.shake * 22)
            out.blit(c, (random.randint(-m, m), random.randint(-m, m)))
        self._present(out)

    def _draw_gameover(self, c):
        a = min(1.0, self.dead_t / 0.35)
        panel = pygame.Surface((250, 190), pygame.SRCALPHA)
        pygame.draw.rect(panel, (240, 250, 255, 235), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, (70, 140, 190), panel.get_rect(), 3, border_radius=18)
        panel.set_alpha(int(255 * a))
        c.blit(panel, ((W - 250) // 2, 150 - int((1 - a) * 40)))
        if a >= 1.0:
            self.text(c, "Game Over", self.font_mid, (W // 2, 188), (200, 60, 50))
            self.text(c, f"Puntos: {self.score}", self.font_mid, (W // 2, 238), (30, 70, 110))
            self.text(c, f"Récord: {self.best}", self.font_sm, (W // 2, 278), (30, 70, 110))
            if self.new_best:
                self.text(c, "¡Nuevo récord!", self.font_sm, (W // 2, 310), (230, 130, 20))
            if self.dead_t > 0.55 and int(self.t * 2) % 2 == 0:
                self.text(c, "Toca para reintentar", self.font_sm, (W // 2, 372))

    def _present(self, surf):
        sw, sh = self.screen.get_size()
        k = min(sw / W, sh / H)
        tw, th = max(1, int(W * k)), max(1, int(H * k))
        self.screen.fill((14, 30, 48))
        scaled = pygame.transform.smoothscale(surf, (tw, th)) if k != 1 else surf
        self.screen.blit(scaled, ((sw - tw) // 2, (sh - th) // 2))
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 1 / 20)
            for ev in pygame.event.get():
                self.handle(ev)
            self.update(dt)
            self.draw()
        pygame.quit()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    fs = None
    if "--fullscreen" in argv:
        fs = True
    elif "--windowed" in argv:
        fs = False
    Game(fs).run()


if __name__ == "__main__":
    main()
