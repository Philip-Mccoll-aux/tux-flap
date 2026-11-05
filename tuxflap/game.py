# SPDX-License-Identifier: GPL-3.0-or-later
"""Tux Flap - un juego estilo Flappy Bird con el pingüino Tux y témpanos cilíndricos.

Resolución lógica vertical (360x640) escalada a cualquier pantalla, pensada
para móviles Linux (Plasma Mobile) pero jugable también con ratón o teclado.

A medida que sube el puntaje el mundo muta: del Edén de Hielo al Apocalipsis.
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
PIPE_W = 66
CAP_W = 82
CAP_H = 26
TUX_X = 96
TUX_R = 17  # radio de colisión
PAD = 12  # margen superior del sprite de Tux
BOT = 6  # margen inferior (pies colgando)
XPAD = 14  # margen lateral (alas grandes)
TUX_W = 54 + 2 * XPAD
TUX_H = 62 + PAD + BOT
TUX_OFF = (PAD - BOT) / 2  # el centro del cuerpo no coincide con el de la imagen

BASE_SPEED = 150.0
BASE_GAP = 168.0
BASE_SPACING = 215.0

APP_ID = "io.github.philip_mccoll_aux.TuxFlap"

READY, PLAYING, DEAD = range(3)

# Puntaje necesario para entrar a cada nivel
LEVEL_SCORES = (0, 8, 16, 26, 38)
LEVELS = (
    dict(name="Edén de Hielo", sub="Todo comienza en paz", dead="Congelado"),
    dict(name="El Deshielo", sub="Algo despierta bajo el hielo", dead="Derretido"),
    dict(name="Plaga de Fuego", sub="Y el cielo ardió", dead="Calcinado"),
    dict(name="Langostas y Relámpagos", sub="Se abrió el abismo", dead="Devorado"),
    dict(name="Apocalipsis", sub="Ya no hay vuelta atrás", dead="Consumado"),
)
AMP = (0, 0, 0, 22, 38)  # oscilación vertical de las columnas
TUX_FORM = (0, 0, 0, 1, 2)  # sprite: normal, alas blancas, serafín de seis alas
AURA = ((0, 0), (40, 60), (50, 80), (64, 100), (86, 130))  # radio, opacidad del aura dorada
HALO = (0, 0, 1, 2, 3)  # nivel de la aureola

# Paletas por nivel
THEMES = (
    dict(sky=((88, 160, 214), (200, 232, 248)), far=((150, 190, 220), (245, 250, 255)),
         near=((112, 160, 200), (250, 253, 255)),
         pipe=((92, 168, 214), (158, 220, 245), (232, 250, 255)), crack=(255, 255, 255, 70),
         edge=(70, 140, 190), spike=((170, 226, 247), (110, 180, 220)),
         ground=((236, 246, 252), (205, 228, 242), (170, 205, 228), (250, 253, 255)), orb=None, seam=False),
    dict(sky=((110, 104, 150), (250, 196, 136)), far=((150, 140, 160), (220, 210, 200)),
         near=((110, 110, 130), (190, 185, 185)),
         pipe=((70, 130, 160), (120, 180, 195), (200, 235, 235)), crack=(255, 255, 255, 50),
         edge=(60, 110, 140), spike=((150, 205, 220), (90, 150, 175)),
         ground=((200, 206, 205), (150, 160, 160), (110, 120, 125), (225, 230, 228)),
         orb=("sun", (250, 210, 150)), seam=False),
    dict(sky=((58, 10, 12), (210, 78, 22)), far=((90, 30, 24), (255, 120, 30)),
         near=((54, 20, 18), (255, 150, 40)),
         pipe=((34, 18, 18), (86, 38, 28), (170, 80, 36)), crack=(255, 150, 40, 230),
         edge=(20, 8, 8), spike=((190, 70, 20), (255, 150, 40)),
         ground=((60, 26, 20), (38, 18, 16), (255, 110, 20), (255, 160, 40)),
         orb=("sun", (255, 90, 30)), seam=True),
    dict(sky=((12, 6, 20), (116, 18, 26)), far=((40, 14, 26), (220, 40, 40)),
         near=((22, 8, 16), (255, 70, 50)),
         pipe=((16, 8, 14), (58, 18, 28), (150, 40, 52)), crack=(255, 60, 50, 230),
         edge=(8, 2, 6), spike=((120, 24, 30), (220, 50, 50)),
         ground=((40, 14, 18), (22, 8, 12), (200, 30, 30), (255, 70, 50)),
         orb=("moon", (200, 30, 30)), seam=True),
    dict(sky=((0, 0, 0), (150, 16, 8)), far=((30, 6, 6), (255, 160, 40)),
         near=((14, 4, 4), (255, 210, 90)),
         pipe=((150, 30, 10), (240, 104, 22), (255, 226, 130)), crack=(255, 240, 160, 220),
         edge=(110, 20, 6), spike=((255, 200, 70), (220, 90, 20)),
         ground=((50, 10, 8), (26, 6, 6), (255, 120, 20), (255, 220, 100)),
         orb=("eclipse", None), seam=True),
)

# Partículas ambientales por nivel: color, velocidad vertical (base, extra), deriva horizontal
FLAKES = (
    ((255, 255, 255), (28, 24), 0),
    ((210, 225, 240), (60, 50), -10),
    ((255, 150, 40), (-30, -40), 0),
    ((150, 130, 130), (20, 25), -25),
    ((255, 200, 80), (-60, -70), 0),
)


def level_for(score):
    return sum(1 for s in LEVEL_SCORES[1:] if score >= s)


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


def approach(v, target, step):
    return min(target, v + step) if v < target else max(target, v - step)


# ------------------------------------------------------------------ gráficos
def glow(pos, color, r_max, r_min, a_max):
    s = pygame.Surface((W, H), pygame.SRCALPHA)
    steps = 14
    for i in range(steps):
        r = int(lerp(r_max, r_min, i / (steps - 1)))
        pygame.draw.circle(s, (*color, int(a_max * (i + 1) / steps)), pos, r)
    return s


def make_sky(theme):
    s = pygame.Surface((W, H))
    top, bot = theme["sky"]
    for y in range(H):
        pygame.draw.line(s, mix(top, bot, y / H), (0, y), (W, y))
    orb = theme["orb"]
    if orb:
        kind, col = orb
        if kind == "sun":
            s.blit(glow((90, 350), col, 150, 40, 150), (0, 0))
            pygame.draw.circle(s, mix(col, (255, 255, 255), 0.4), (90, 350), 38)
        elif kind == "moon":
            s.blit(glow((265, 140), col, 120, 46, 130), (0, 0))
            pygame.draw.circle(s, (190, 30, 30), (265, 140), 46)
            for dx, dy, r in ((-14, -10, 9), (12, 8, 12), (-6, 20, 6), (18, -18, 5)):
                pygame.draw.circle(s, (140, 20, 24), (265 + dx, 140 + dy), r)
        elif kind == "eclipse":
            s.blit(glow((235, 170), (255, 140, 40), 150, 56, 200), (0, 0))
            pygame.draw.circle(s, (255, 230, 170), (235, 170), 57, 3)
            pygame.draw.circle(s, (0, 0, 0), (235, 170), 54)
    return s


def make_mountains(seed, amp, col, cap):
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
        c = [(px, py), (px - 16, py + 26), (px - 5, py + 20), (px + 4, py + 28), (px + 16, py + 24)]
        pygame.draw.polygon(s, cap, c)
    return s


def make_cylinder(width, height, pal, crack):
    """Columna cilíndrica con degradado horizontal y brillos."""
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    dark, mid, light = pal
    for x in range(width):
        t = x / (width - 1)
        k = math.sin(t * math.pi)
        c = mix(dark, mid, k) if t > 0.28 else mix(mid, light, 1 - t / 0.28)
        c = mix(c, light, max(0.0, 1 - abs(t - 0.24) / 0.09) * 0.7)
        pygame.draw.line(s, c, (x, 0), (x, height))
    rnd = random.Random(7)
    for _ in range(height // 22):
        x = rnd.randint(8, width - 9)
        y = rnd.randint(0, height)
        x2, y2 = x + rnd.randint(-3, 3), y + rnd.randint(14, 40)
        if crack[3] > 120:  # grietas incandescentes
            pygame.draw.line(s, (*crack[:3], 70), (x, y), (x2, y2), 5)
        pygame.draw.line(s, crack, (x, y), (x2, y2), 1)
    return s


def make_cap(width, height, pal, crack, edge):
    s = pygame.Surface((width, height), pygame.SRCALPHA)
    s.blit(make_cylinder(width, height, pal, crack), (0, 0))
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, width, height), border_radius=9)
    s.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.rect(s, edge, (0, 0, width, height), 2, border_radius=9)
    return s


def make_ground(theme):
    top, body, tooth, line = theme["ground"]
    s = pygame.Surface((W + 48, GROUND_H))
    s.fill(top)
    pygame.draw.rect(s, body, (0, 10, W + 48, GROUND_H - 10))
    for x in range(0, W + 48, 24):
        pygame.draw.polygon(s, tooth, [(x, 22), (x + 12, 22), (x + 6, 44)])
    if theme["seam"]:
        for x in range(0, W + 48, 48):
            pygame.draw.lines(s, line, False, [(x, 52), (x + 12, 62), (x + 6, 70), (x + 20, GROUND_H)], 2)
    pygame.draw.line(s, line, (0, 0), (W + 48, 0), 4)
    return s


def make_assets(theme):
    pipe, crack, edge = theme["pipe"], theme["crack"], theme["edge"]
    cap = make_cap(CAP_W, CAP_H, pipe, crack, edge)
    return dict(
        sky=make_sky(theme),
        far=make_mountains(1, 150, theme["far"][0], theme["far"][1]),
        near=make_mountains(2, 110, theme["near"][0], theme["near"][1]),
        cyl=make_cylinder(PIPE_W, H, pipe, crack),
        cap=cap,
        cap_flip=pygame.transform.flip(cap, False, True),
        ground=make_ground(theme),
        spike=theme["spike"],
    )


def make_vignette():
    sw, sh = 36, 64
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            dx, dy = (x / (sw - 1) - 0.5) * 2, (y / (sh - 1) - 0.5) * 2
            d = min(1.0, math.hypot(dx, dy) / 1.25)
            s.set_at((x, y), (50, 0, 0, int(255 * d ** 2.4)))
    return pygame.transform.smoothscale(s, (W, H))


def make_tux(wing=3, form=0, eyes="open", feet=0):
    """Tux dibujado con primitivas, 4x supermuestreado.
    wing: 0 alas arriba .. 5 alas abajo.
    form: 0 normal, 1 alas blancas de plumas, 2 serafín de seis alas.
    eyes: open | blink | scared | dead.  feet: 0 recogidos, 1 colgando."""
    S = 4
    w, h = TUX_W, TUX_H
    big = pygame.Surface((w * S, h * S), pygame.SRCALPHA)

    def E(color, rect, width=0):
        x, y, rw, rh = rect
        pygame.draw.ellipse(big, color, ((x + XPAD) * S, (y + PAD) * S, rw * S, rh * S), width * S)

    def L(color, a, b, wd):
        pygame.draw.line(big, color, ((a[0] + XPAD) * S, (a[1] + PAD) * S), ((b[0] + XPAD) * S, (b[1] + PAD) * S),
                         int(wd * S))

    def wing_surf(ww, wh, angel):
        surf = pygame.Surface((ww * S, wh * S), pygame.SRCALPHA)
        if not angel:
            pygame.draw.ellipse(surf, (28, 28, 34), surf.get_rect())
            return surf
        # plumas superpuestas, de abajo hacia arriba
        for i, fy in enumerate((0.42, 0.22, 0.0)):
            r = pygame.Rect(0, int(fy * wh * S), ww * S, int(wh * S * 0.58))
            pygame.draw.ellipse(surf, (250, 250, 255), r)
            pygame.draw.ellipse(surf, (176, 196, 226), r, int(1.4 * S))
        return surf

    def put_wing(cx, cy, surf, ang):
        r = pygame.transform.rotate(surf, ang)
        big.blit(r, ((cx + XPAD) * S - r.get_width() // 2, (cy + PAD) * S - r.get_height() // 2))

    black, white, orange = (28, 28, 34), (250, 250, 250), (250, 168, 30)
    if feet == 0:
        E(orange, (10, 52, 18, 9))
        E(orange, (26, 52, 18, 9))
    else:
        for cx, ang in ((15, 24), (39, -24)):
            fs = pygame.Surface((18 * S, 9 * S), pygame.SRCALPHA)
            pygame.draw.ellipse(fs, orange, fs.get_rect())
            put_wing(cx, 60, fs, ang)
    k = wing / 5.0
    wy = lerp(-8, 16, k)
    base = lerp(42, -30, k)
    for cx, sign in ((3, -1), (53, 1)):
        if form == 0:
            put_wing(cx, 22 + wy + 15, wing_surf(14, 30, False), sign * base)
        elif form == 1:
            put_wing(cx, 22 + wy + 17, wing_surf(18, 36, True), sign * base)
        else:  # serafín: tres pares
            put_wing(cx - sign * 1, 22 + wy + 3, wing_surf(14, 28, True), sign * (base + 30))
            put_wing(cx - sign * 1, 22 + wy + 31, wing_surf(14, 28, True), sign * (base - 32))
            put_wing(cx, 22 + wy + 17, wing_surf(19, 38, True), sign * base)
    E(black, (6, 4, 42, 54))
    E(white, (14, 22, 26, 33))
    E(white, (12, 11, 12, 13))
    E(white, (30, 11, 12, 13))
    E(black, (14, 8, 26, 14))
    for ex in (17, 29):
        if eyes == "blink":
            E(white, (ex, 11, 9, 11))
            L(black, (ex + 0.5, 17), (ex + 8.5, 17), 2.2)
        elif eyes == "scared":
            E(white, (ex - 1, 10, 11, 13))
            E(black, (ex + 3.5, 15, 3, 3))
        elif eyes == "dead":
            E(white, (ex, 11, 9, 11))
            L(black, (ex + 1.5, 13), (ex + 7.5, 20), 1.8)
            L(black, (ex + 7.5, 13), (ex + 1.5, 20), 1.8)
        else:
            E(white, (ex, 11, 9, 11))
            E(black, (ex + 4, 14, 4, 5))
    E(orange, (17, 20, 20, 9))
    E((222, 140, 20), (20, 26, 14, 5))
    return pygame.transform.smoothscale(big, (w, h))


def make_aura(r, alpha):
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    steps = 16
    for i in range(steps):
        rr = int(lerp(r, 6, i / (steps - 1)))
        pygame.draw.circle(s, (255, 228, 140, int(alpha * ((i + 1) / steps) ** 1.6)), (r, r), rr)
    return s


def make_rays(size=200, n=12):
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    for i in range(n):
        a = i * 2 * math.pi / n
        pts = [(c, c)] + [(c + math.cos(a + d) * c, c + math.sin(a + d) * c) for d in (-0.07, 0.07)]
        pygame.draw.polygon(s, (255, 240, 170, 70), pts)
    return s


def make_icon_surface(size=128):
    t = make_tux(3)
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 190, 232), (size // 2, size // 2), size // 2)
    th = int(size * 0.72)
    t = pygame.transform.smoothscale(t, (int(TUX_W * th / TUX_H), th))
    s.blit(t, ((size - t.get_width()) // 2, (size - t.get_height()) // 2))
    return s


# ------------------------------------------------------------------- sonido
def make_sounds():
    snd = {}
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        rate = pygame.mixer.get_init()[0]

        def to_sound(samples):
            buf = bytearray()
            for v in samples:
                buf += int(v).to_bytes(2, "little", signed=True)
            return pygame.mixer.Sound(buffer=bytes(buf))

        def tone(freqs, dur, vol=0.35):
            n = int(rate * dur)
            return to_sound(32767 * vol * (1 - i / n) *
                            math.sin(2 * math.pi * lerp(freqs[0], freqs[-1], i / n) * i / rate)
                            for i in range(n))

        def thunder(dur=0.8, vol=0.55):
            n = int(rate * dur)
            rnd = random.Random(3)
            out, prev = [], 0.0
            for i in range(n):
                prev = prev * 0.94 + rnd.uniform(-1, 1) * 0.06
                out.append(32767 * vol * 4 * prev * (1 - i / n) ** 2)
            return to_sound(out)

        snd["flap"] = tone((420, 760), 0.09)
        snd["score"] = tone((880, 1320), 0.14)
        snd["hit"] = tone((300, 70), 0.30, 0.5)
        snd["level"] = tone((330, 990), 0.55, 0.3)
        snd["thunder"] = thunder()
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
        self.buf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()

        self.assets = [make_assets(t) for t in THEMES]
        self.tux_cache = {}
        self.warm = [(k, v, e, f) for v in range(3) for e in ("open", "blink", "scared", "dead")
                     for f in (0, 1) for k in range(6)]
        self.vignette = make_vignette()
        self.auras = [make_aura(r, a) if r else None for r, a in AURA]
        self.rays = make_rays()
        self.flash_surf = pygame.Surface((W, H))
        self.flash_surf.fill((255, 255, 255))
        self.font_big = pygame.font.Font(None, 96)
        self.font_mid = pygame.font.Font(None, 44)
        self.font_ban = pygame.font.Font(None, 36)
        self.font_sm = pygame.font.Font(None, 30)
        self.sounds = make_sounds()
        self.flakes = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.5, 1.6)] for _ in range(46)]
        self.locusts = [[random.uniform(0, W), random.uniform(60, GROUND_Y - 40), random.uniform(0, 6.3),
                         random.uniform(150, 240)] for _ in range(34)]
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
        self.pipes = []  # [x, centro_base, puntuado, fase]
        self.score = 0
        self.t = 0.0
        self.pt = 0.0  # tiempo de juego (mueve las columnas)
        self.dead_t = 0.0
        self.shake = 0.0
        self.new_best = False
        self.scroll = 0.0
        self.lvl = 0
        self.prev = 0
        self.mix = 1.0
        self.banner_t = 0.0
        self.speed = BASE_SPEED
        self.gap = BASE_GAP
        self.amp = 0.0
        self.flash = 0.0
        self.bolt = None
        self.bolt_t = 0.0
        self.next_bolt = random.uniform(1.5, 3.5)
        self.meteors = []
        self.meteor_cd = 0.0
        self.trail = []
        self.puffs = []
        self.ang = 0.0
        self.spin = 0.0
        self.rest = 80.0
        self.bounces = 0
        self.landed = False
        self.flap_t = 9.0
        self.sq = 0.0
        self.wing_k = 0.5
        self.blink_t = 0.0
        self.blink_cd = random.uniform(1.0, 3.0)
        for i in range(4):
            self._add_pipe(W + 120 + i * BASE_SPACING)

    def _bounds(self):
        return 60 + self.gap / 2, GROUND_Y - 60 - self.gap / 2

    def _add_pipe(self, x):
        lo, hi = self._bounds()
        m = AMP[self.lvl]
        prev = self.pipes[-1][1] if self.pipes else (lo + hi) / 2
        c = min(hi - m, max(lo + m, prev + random.uniform(-190, 190)))
        self.pipes.append([x, c, False, random.uniform(0, 6.3)])

    def center(self, p):
        lo, hi = self._bounds()
        return min(hi, max(lo, p[1] + self.amp * math.sin(self.pt * 1.7 + p[3])))

    def flap(self):
        if self.state == READY:
            self.state = PLAYING
        if self.state == PLAYING:
            self.vy = FLAP_V
            self.flap_t = 0.0
            self.sq = 1.0
            for _ in range(3):
                self.puffs.append([TUX_X - 10, self.y + 8, random.uniform(-80, -25), random.uniform(30, 90),
                                   0.32, 0.32, (255, 255, 255), 3, 0.0, "p"])
            if TUX_FORM[self.lvl] >= 1:
                for _ in range(2):
                    self.puffs.append([TUX_X - 14, self.y + 4, random.uniform(-60, -20), random.uniform(-20, 20), 0.9, 0.9,
                                       (240, 244, 255), 3, 90.0, "f"])
            self._play("flap")

    def _play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()

    def _check_level(self):
        new = level_for(self.score)
        if new > self.lvl:
            self.prev, self.lvl, self.mix = self.lvl, new, 0.0
            self.banner_t = 3.4
            self._play("level")
            for _ in range(24):
                self.puffs.append([TUX_X, self.y, random.uniform(-140, 140), random.uniform(-150, 40), 0.9, 0.9,
                                   (255, 232, 150), 3, -30.0, "p"])
            if new >= 2:
                self.strike(bolt=False)

    def strike(self, bolt=True):
        self.flash = 1.0
        self.shake = max(self.shake, 0.2)
        self._play("thunder")
        if bolt:
            x = random.uniform(40, W - 40)
            pts = [(x, 0)]
            y = 0
            while y < GROUND_Y:
                y += random.uniform(30, 55)
                x += random.uniform(-26, 26)
                pts.append((x, min(y, GROUND_Y)))
            self.bolt, self.bolt_t = pts, 0.16

    def die(self):
        self.state = DEAD
        self.dead_t = 0.0
        self.shake = 0.35
        self.spin = random.choice((-1, 1)) * random.uniform(420, 640)
        self.bounces = 0
        self.landed = False
        self.vy = -150.0  # rebote al chocar
        for _ in range(16):
            self.puffs.append([TUX_X, self.y, random.uniform(-150, 150), random.uniform(-220, -40), 1.0, 1.0,
                               random.choice(((28, 28, 34), (245, 245, 245))), 3, 420.0, "f"])
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

    # -- ambiente (corre siempre)
    def _update_ambience(self, dt):
        L = self.lvl
        if self.mix < 1:
            self.mix = min(1.0, self.mix + dt / 1.8)
        self.banner_t = max(0.0, self.banner_t - dt)
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)
        if self.bolt_t > 0:
            self.bolt_t -= dt

        col, (vb, vx), drift = FLAKES[L]
        for f in self.flakes:
            vy = vb + vx * f[2]
            f[1] += vy * dt
            f[0] += (math.sin(self.t * 0.8 + f[1] * 0.02) * 12 + drift) * dt
            if vy > 0 and f[1] > H:
                f[0], f[1] = random.uniform(0, W + 40), -4
            elif vy < 0 and f[1] < -4:
                f[0], f[1] = random.uniform(0, W), H + 4
            f[0] %= W + 40

        if L >= 3:
            for lc in self.locusts:
                lc[0] -= lc[3] * dt
                lc[1] += math.sin(self.t * 5 + lc[2]) * 40 * dt
                if lc[0] < -10:
                    lc[0], lc[1] = W + random.uniform(10, 80), random.uniform(60, GROUND_Y - 40)
            if L >= 3 and self.state != READY:
                self.next_bolt -= dt
                if self.next_bolt <= 0:
                    self.strike()
                    self.next_bolt = random.uniform(2.5, 6) if L == 3 else random.uniform(1.5, 4)
        if L >= 4:
            self.meteor_cd -= dt
            if self.meteor_cd <= 0:
                self.meteor_cd = random.uniform(0.15, 0.4)
                self.meteors.append([random.uniform(W * 0.3, W + 120), -20, -170, 330])
        for m in self.meteors:
            m[0] += m[2] * dt
            m[1] += m[3] * dt
        self.meteors = [m for m in self.meteors if m[1] < GROUND_Y and m[0] > -40]
        for tr in self.trail:
            tr[0] += tr[2] * dt
            tr[1] += tr[3] * dt
            tr[4] -= dt
        self.trail = [tr for tr in self.trail if tr[4] > 0]

    # -- animación de Tux
    def _land(self):
        self.landed = True
        self.ang = (self.ang + 180) % 360 - 180
        self.rest = 80.0 if self.ang >= 0 else -80.0
        self._dust()

    def _dust(self):
        for _ in range(6):
            self.puffs.append([TUX_X + random.uniform(-10, 10), GROUND_Y - 2, random.uniform(-70, 70),
                               random.uniform(-60, -15), 0.4, 0.4, (235, 240, 245), 4, 0.0, "p"])

    def _update_anim(self, dt):
        self.flap_t += dt
        self.sq = max(0.0, self.sq - dt / 0.22)
        self.blink_cd -= dt
        if self.blink_cd <= 0:
            self.blink_t, self.blink_cd = 0.13, random.uniform(2.0, 4.5)
        self.blink_t = max(0.0, self.blink_t - dt)
        if self.state == READY:
            self.wing_k = 0.5 + 0.5 * math.sin(self.t * 6)
            self.ang = math.sin(self.t * 3) * 5
        elif self.state == DEAD:
            self.wing_k = approach(self.wing_k, 0.0, 6 * dt)
        else:
            if self.flap_t < 0.30:
                p = self.flap_t / 0.30
                self.wing_k = p / 0.55 if p < 0.55 else lerp(1.0, 0.4, (p - 0.55) / 0.45)
            else:
                self.wing_k = approach(self.wing_k, 0.05 if self.vy > 250 else 0.45, 5 * dt)
            target = max(-28.0, min(70.0, self.vy * 0.09))
            self.ang += (target - self.ang) * (1 - math.exp(-14 * dt))
        for p in self.puffs:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[3] += p[8] * dt
            p[4] -= dt
        self.puffs = [p for p in self.puffs if p[4] > 0]
        if self.warm:  # precarga los sprites de a uno por cuadro
            k, v, e, f = self.warm.pop(0)
            self.tux_img(k, v, e, f)

    def tux_img(self, k, variant, eyes, feet):
        key = (k, variant, eyes, feet)
        im = self.tux_cache.get(key)
        if im is None:
            im = self.tux_cache[key] = make_tux(k, variant, eyes, feet)
        return im

    # -- física
    def update(self, dt):
        self.t += dt
        self._update_ambience(dt)

        self._update_anim(dt)
        if self.state == DEAD:
            self.dead_t += dt
            gy = GROUND_Y - TUX_R
            if not self.landed and (self.y < gy - 0.5 or self.vy < 0):
                self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
                self.y = min(gy, self.y + self.vy * dt)
                self.ang += self.spin * dt
                if self.y >= gy:
                    if self.bounces < 1:
                        self.bounces += 1
                        self.vy = -max(140.0, self.vy * 0.3)
                        self.spin *= 0.4
                        self.shake = max(self.shake, 0.12)
                        self._dust()
                    else:
                        self.vy = 0.0
                        self._land()
            elif not self.landed:
                self._land()
            else:
                self.ang = approach(self.ang, self.rest, 500 * dt)
            return

        self.scroll = (self.scroll + self.speed * dt) % 48
        if self.state == READY:
            self.y = H * 0.42 + math.sin(self.t * 4) * 8
            return

        self.pt += dt
        L = self.lvl
        self.speed = approach(self.speed, BASE_SPEED + 10 * L, 25 * dt)
        self.gap = approach(self.gap, BASE_GAP - 6 * L, 15 * dt)
        self.amp = approach(self.amp, AMP[L], 12 * dt)

        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
        self.y += self.vy * dt
        for p in self.pipes:
            p[0] -= self.speed * dt
            if not p[2] and p[0] + PIPE_W / 2 < TUX_X:
                p[2] = True
                self.score += 1
                self._play("score")
                self._check_level()
        if self.pipes and self.pipes[0][0] + CAP_W / 2 < -10:
            self.pipes.pop(0)
            self._add_pipe(self.pipes[-1][0] + BASE_SPACING + 15 * self.lvl)

        if L >= 1:  # estela de destellos dorados
            self.trail.append([TUX_X - 12, self.y + random.uniform(-2, 8), -self.speed * 0.4 + random.uniform(-20, 20),
                               random.uniform(-20, 40), 0.5])

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
        for p in self.pipes:
            x, c = p[0], self.center(p)
            top_end, bot_start = c - self.gap / 2, c + self.gap / 2
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
        sh = font.render(s, True, (20, 30, 50))
        im = font.render(s, True, color)
        r = im.get_rect(center=pos) if center else im.get_rect(topleft=pos)
        surf.blit(sh, r.move(2, 3))
        surf.blit(im, r)

    def draw_world(self, surf, L):
        A = self.assets[L]
        surf.blit(A["sky"], (0, 0))
        for key, speed, y in (("far", 6, GROUND_Y - 250), ("near", 18, GROUND_Y - 235)):
            img = A[key]
            iw = img.get_width()
            ox = -((self.t * speed) % iw)
            surf.blit(img, (ox, y))
            surf.blit(img, (ox + iw, y))
        sp_fill, sp_edge = A["spike"]
        for p in self.pipes:
            x, cy = p[0], self.center(p)
            top_end, bot_start = int(cy - self.gap / 2), int(cy + self.gap / 2)
            th = max(0, top_end - CAP_H)
            surf.blit(A["cyl"], (x - PIPE_W / 2, 0), (0, H - th, PIPE_W, th))
            surf.blit(A["cap_flip"], (x - CAP_W / 2, top_end - CAP_H))
            surf.blit(A["cap"], (x - CAP_W / 2, bot_start))
            surf.blit(A["cyl"], (x - PIPE_W / 2, bot_start + CAP_H), (0, 0, PIPE_W, GROUND_Y - bot_start - CAP_H))
            tip = [(x - 14, top_end), (x + 14, top_end), (x, top_end + 20)]
            pygame.draw.polygon(surf, sp_fill, tip)
            pygame.draw.polygon(surf, sp_edge, tip, 2)
        surf.blit(A["ground"], (-self.scroll, GROUND_Y))

    def draw(self):
        c = self.canvas
        L = self.lvl
        if self.mix < 1:
            self.draw_world(c, self.prev)
            self.draw_world(self.buf, L)
            self.buf.set_alpha(int(255 * self.mix))
            c.blit(self.buf, (0, 0))
        else:
            self.draw_world(c, L)

        if L >= 3:  # langostas
            for x, y, ph, _ in self.locusts:
                fl = 3 if int(self.t * 22 + ph * 3) % 2 else 1
                pygame.draw.ellipse(c, (60, 34, 16), (x, y, 6, 3))
                pygame.draw.line(c, (140, 100, 50), (x + 2, y), (x, y - fl), 1)
        for mx, my, vx, vy in self.meteors:  # lluvia de fuego
            pygame.draw.line(c, (255, 140, 40), (mx, my), (mx - vx * 0.09, my - vy * 0.09), 4)
            pygame.draw.line(c, (255, 220, 140), (mx, my), (mx - vx * 0.04, my - vy * 0.04), 2)
            pygame.draw.circle(c, (255, 250, 220), (int(mx), int(my)), 3)

        tcol = (255, 236, 150) if L < 4 else (255, 250, 215)
        for x, y, _, _, life in self.trail:
            pygame.draw.circle(c, tcol, (int(x), int(y)), 1 + int(life * 5))

        if AURA[L][0]:
            pulse = 0.75 + 0.25 * math.sin(self.t * 3)
            if L >= 4:
                r = pygame.transform.rotate(self.rays, self.t * 18)
                r.set_alpha(int(255 * pulse))
                c.blit(r, r.get_rect(center=(TUX_X, self.y)))
            au = self.auras[L]
            au.set_alpha(int(255 * pulse))
            c.blit(au, au.get_rect(center=(TUX_X, self.y)))
        for x, y, _, _, life, maxl, pcol, sz, _, kind in self.puffs:
            f = life / maxl
            if kind == "p":
                pygame.draw.circle(c, pcol, (int(x), int(y)), max(1, int(sz * (0.4 + f))))
            else:  # pluma
                r = (1 - f) * 14
                pygame.draw.line(c, pcol, (x, y), (x + math.cos(r) * 6, y + math.sin(r) * 3), 3)

        form = TUX_FORM[L]
        playing = self.state == PLAYING
        if self.state == DEAD:
            eyes = "dead"
        elif self.blink_t > 0:
            eyes = "blink"
        elif playing and self.vy > 420:
            eyes = "scared"
        else:
            eyes = "open"
        feet = 1 if (self.state == DEAD or (playing and self.vy > 150)) else 0
        img = self.tux_img(int(round(self.wing_k * 5)), form, eyes, feet)
        fall = min(1.0, max(0.0, (self.vy - 300) / 400)) if playing else 0.0
        sx = 1 - 0.14 * self.sq - 0.07 * fall
        sy = 1 + 0.20 * self.sq + 0.10 * fall
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * sx)), max(1, int(img.get_height() * sy))))
        img = pygame.transform.rotozoom(img, -self.ang, 1.0)
        c.blit(img, img.get_rect(center=(TUX_X, self.y - TUX_OFF)))
        th = math.radians(self.ang)
        if HALO[L]:
            self._draw_halo(c, th, HALO[L])
        if self.state == DEAD and self.landed:
            self._draw_stars(c, th)

        col, _, _ = FLAKES[L]
        for fx, fy, sz in self.flakes:
            pygame.draw.circle(c, col, (int(fx), int(fy)), 1 + int(sz > 1.1))

        if self.bolt_t > 0 and self.bolt:
            pygame.draw.lines(c, (190, 190, 255), False, self.bolt, 7)
            pygame.draw.lines(c, (255, 255, 255), False, self.bolt, 3)
        if self.flash > 0:
            self.flash_surf.set_alpha(int(170 * self.flash))
            c.blit(self.flash_surf, (0, 0))

        vig = lerp((0, 0, 70, 150, 230)[self.prev], (0, 0, 70, 150, 230)[L], self.mix)
        if vig > 0:
            self.vignette.set_alpha(int(vig))
            c.blit(self.vignette, (0, 0))

        # HUD
        if self.state == PLAYING:
            self.text(c, str(self.score), self.font_big, (W // 2, 70))
        elif self.state == READY:
            self.text(c, "Tux Flap", self.font_big, (W // 2, 130))
            self.text(c, "Toca para aletear", self.font_mid, (W // 2, 210))
            self.text(c, f"Récord: {self.best}", self.font_sm, (W // 2, GROUND_Y + 40))
        else:
            self._draw_gameover(c)
        if self.banner_t > 0 and self.state == PLAYING:
            self._draw_banner(c)

        out = c
        if self.shake > 0:
            out = pygame.Surface((W, H))
            m = int(self.shake * 22)
            out.blit(c, (random.randint(-m, m), random.randint(-m, m)))
        self._present(out)

    def _draw_halo(self, c, th, level):
        d = 34 + 3 * math.sin(self.t * 4)
        pulse = 0.6 + 0.4 * math.sin(self.t * 6)
        rw, rh = ((28, 10), (34, 12), (42, 15))[level - 1]
        s = pygame.Surface((rw + 18, rh + 14), pygame.SRCALPHA)
        cx, cy = s.get_width() // 2, s.get_height() // 2
        pygame.draw.ellipse(s, (255, 214, 64, int((70 + 30 * level) * pulse)), s.get_rect())
        pygame.draw.ellipse(s, (255, 226, 96), (cx - rw // 2, cy - rh // 2, rw, rh), 3)
        if level >= 2:
            pygame.draw.ellipse(s, (255, 248, 200), (cx - rw // 2 + 3, cy - rh // 2 + 2, rw - 6, rh - 4), 1)
        r = pygame.transform.rotate(s, -self.ang)
        c.blit(r, r.get_rect(center=(TUX_X + d * math.sin(th), self.y - d * math.cos(th))))

    def _draw_stars(self, c, th):
        bx, by = TUX_X + 34 * math.sin(th), self.y - 34 * math.cos(th)
        for i in range(3):
            a = self.t * 5 + i * 2.094
            x, y = bx + math.cos(a) * 20, by + math.sin(a) * 6
            pts = [(x + math.cos(k * math.pi / 4) * (5 if k % 2 == 0 else 2),
                    y + math.sin(k * math.pi / 4) * (5 if k % 2 == 0 else 2)) for k in range(8)]
            pygame.draw.polygon(c, (255, 225, 90), pts)

    def _draw_banner(self, c):
        a = min(1.0, self.banner_t / 0.5, (3.4 - self.banner_t) / 0.4)
        s = pygame.Surface((W, 110), pygame.SRCALPHA)
        info = LEVELS[self.lvl]
        self.text(s, f"NIVEL {self.lvl + 1}", self.font_sm, (W // 2, 16), (255, 210, 120))
        self.text(s, info["name"], self.font_ban, (W // 2, 48))
        self.text(s, info["sub"], self.font_sm, (W // 2, 86), (235, 220, 210))
        s.set_alpha(int(255 * a))
        c.blit(s, (0, 120))

    def _draw_gameover(self, c):
        a = min(1.0, self.dead_t / 0.35)
        panel = pygame.Surface((250, 190), pygame.SRCALPHA)
        pygame.draw.rect(panel, (240, 250, 255, 235), panel.get_rect(), border_radius=18)
        pygame.draw.rect(panel, (70, 140, 190), panel.get_rect(), 3, border_radius=18)
        panel.set_alpha(int(255 * a))
        c.blit(panel, ((W - 250) // 2, 150 - int((1 - a) * 40)))
        if a >= 1.0:
            self.text(c, LEVELS[self.lvl]["dead"], self.font_mid, (W // 2, 188), (200, 60, 50))
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
