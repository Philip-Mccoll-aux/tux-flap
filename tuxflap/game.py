# SPDX-License-Identifier: GPL-3.0-or-later
"""Tux Flap - un juego estilo Flappy Bird con el pingüino Tux y témpanos cilíndricos.

Resolución lógica vertical (360x640) escalada a cualquier pantalla, pensada
para móviles Linux (Plasma Mobile) pero jugable también con ratón o teclado.

El mundo muta de forma continua y sin techo a medida que avanzas. Un único
parámetro de progreso `u` (0 = Edén de Hielo, 4 = Apocalipsis, y sigue
creciendo) gobierna el entorno y a Tux: la paleta fluye, se abren ojos en el
cielo y en las columnas, y Tux se vuelve un serafín bíblico: más alas, más
plumas, ruedas con ojos... todo generado proceduralmente y acumulativo.
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
TUX_R = 17  # radio de colisión (solo el cuerpo: alas y ruedas son visuales)
PAD = 2  # margen superior del sprite de Tux
BOT = 6  # margen inferior (pies colgando)
TUX_W = 54
TUX_H = 62 + PAD + BOT
TUX_OFF = (PAD - BOT) / 2  # el centro del cuerpo no coincide con el de la imagen

BASE_SPEED = 150.0
BASE_GAP = 168.0
BASE_SPACING = 215.0
SCORE_PER_U = 9.5  # puntos por unidad de progreso (u = 4 -> 38 puntos)

SS = 3  # supermuestreo de las capas de Tux
LW = 200  # lado (lógico) de la capa de Tux

APP_ID = "io.github.philip_mccoll_aux.TuxFlap"

READY, PLAYING, DEAD = range(3)

# Título que aparece al cruzar cada unidad entera de progreso: (nombre, subtítulo, causa de muerte)
NAMES = (
    ("Edén de Hielo", "Todo comienza en paz", "Congelado"),
    ("El Deshielo", "Algo despierta bajo el hielo", "Derretido"),
    ("Plaga de Fuego", "Y el cielo ardió", "Calcinado"),
    ("Langostas y Relámpagos", "Se abrió el abismo", "Devorado"),
    ("Apocalipsis", "Ya no hay vuelta atrás", "Consumado"),
    ("El Séptimo Sello", "Hubo silencio en el cielo", "Juzgado"),
    ("Ruedas con Ojos", "Estaban llenas de ojos", "Visto"),
    ("Mar de Cristal", "Y todo lo ve", "Cegado"),
    ("Gloria sin Nombre", "Más allá de toda forma", "Elevado"),
)

# Paletas clave en u = 0, 1, 2, 3, 4. Entre ellas se interpola de forma continua.
THEMES = (
    dict(sky=((88, 160, 214), (200, 232, 248)), far=((150, 190, 220), (245, 250, 255)),
         near=((112, 160, 200), (250, 253, 255)),
         pipe=((92, 168, 214), (158, 220, 245), (232, 250, 255)), crack=(255, 255, 255, 70),
         edge=(70, 140, 190), spike=((170, 226, 247), (110, 180, 220)),
         ground=((236, 246, 252), (205, 228, 242), (170, 205, 228), (250, 253, 255)), seam=False),
    dict(sky=((110, 104, 150), (250, 196, 136)), far=((150, 140, 160), (220, 210, 200)),
         near=((110, 110, 130), (190, 185, 185)),
         pipe=((70, 130, 160), (120, 180, 195), (200, 235, 235)), crack=(255, 255, 255, 50),
         edge=(60, 110, 140), spike=((150, 205, 220), (90, 150, 175)),
         ground=((200, 206, 205), (150, 160, 160), (110, 120, 125), (225, 230, 228)), seam=False),
    dict(sky=((58, 10, 12), (210, 78, 22)), far=((90, 30, 24), (255, 120, 30)),
         near=((54, 20, 18), (255, 150, 40)),
         pipe=((34, 18, 18), (86, 38, 28), (170, 80, 36)), crack=(255, 150, 40, 230),
         edge=(20, 8, 8), spike=((190, 70, 20), (255, 150, 40)),
         ground=((60, 26, 20), (38, 18, 16), (255, 110, 20), (255, 160, 40)), seam=True),
    dict(sky=((12, 6, 20), (116, 18, 26)), far=((40, 14, 26), (220, 40, 40)),
         near=((22, 8, 16), (255, 70, 50)),
         pipe=((16, 8, 14), (58, 18, 28), (150, 40, 52)), crack=(255, 60, 50, 230),
         edge=(8, 2, 6), spike=((120, 24, 30), (220, 50, 50)),
         ground=((40, 14, 18), (22, 8, 12), (200, 30, 30), (255, 70, 50)), seam=True),
    dict(sky=((0, 0, 0), (150, 16, 8)), far=((30, 6, 6), (255, 160, 40)),
         near=((14, 4, 4), (255, 210, 90)),
         pipe=((150, 30, 10), (240, 104, 22), (255, 226, 130)), crack=(255, 240, 160, 220),
         edge=(110, 20, 6), spike=((255, 200, 70), (220, 90, 20)),
         ground=((50, 10, 8), (26, 6, 6), (255, 120, 20), (255, 220, 100)), seam=True),
)

# Partículas ambientales: color, (velocidad vertical base, extra), deriva horizontal.
# Pasan de nieve que cae, a lluvia, a brasas que suben.
FLAKES = (
    ((255, 255, 255), (28, 24), 0),
    ((210, 225, 240), (60, 50), -10),
    ((255, 150, 40), (-30, -40), 0),
    ((150, 130, 130), (20, 25), -25),
    ((255, 200, 80), (-60, -70), 0),
)

# Ojos del cuerpo de Tux: (x, y, radio, u de apertura), en coordenadas locales al centro del cuerpo
BODY_EYES = ((0, -21, 2.6, 2.9), (-12, -5, 2.4, 3.3), (12, -5, 2.4, 3.6), (0, 6, 3.0, 3.9),
             (-9, 14, 2.6, 4.3), (9, 14, 2.6, 4.6), (0, 22, 2.6, 5.0))
IRIS = ((232, 172, 40), (210, 60, 46), (120, 170, 210), (240, 220, 140))


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


def ramp(v, a, b):
    """0 por debajo de a, 1 por encima de b, lineal entre ambos."""
    return min(1.0, max(0.0, (v - a) / (b - a)))


def blend(a, b, t):
    if isinstance(a, bool):
        return b if t > 0.5 else a
    if isinstance(a, (tuple, list)):
        return tuple(blend(x, y, t) for x, y in zip(a, b))
    return int(round(a + (b - a) * t))


def kf(frames, u):
    """Interpola de forma continua entre fotogramas clave en u = 0, 1, 2..."""
    if u >= len(frames) - 1:
        return frames[-1]
    i = max(0, int(u))
    return blend(frames[i], frames[i + 1], u - i)


def theme_at(u):
    return {k: kf([t[k] for t in THEMES], u) for k in THEMES[0]}


# ------------------------------------------------------------------ gráficos
def glow(size, pos, color, r_max, r_min, a_max):
    s = pygame.Surface(size, pygame.SRCALPHA)
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
    return s


def make_orbs():
    """Sol, luna de sangre y eclipse: se dibujan aparte con opacidad según el progreso."""
    sun = glow((300, 300), (150, 150), (255, 110, 40), 150, 40, 150)
    pygame.draw.circle(sun, (255, 190, 120), (150, 150), 38)
    moon = glow((240, 240), (120, 120), (200, 30, 30), 120, 46, 130)
    pygame.draw.circle(moon, (190, 30, 30), (120, 120), 46)
    for dx, dy, r in ((-14, -10, 9), (12, 8, 12), (-6, 20, 6), (18, -18, 5)):
        pygame.draw.circle(moon, (140, 20, 24), (120 + dx, 120 + dy), r)
    ecl = glow((300, 300), (150, 150), (255, 140, 40), 150, 56, 200)
    pygame.draw.circle(ecl, (255, 230, 170), (150, 150), 57, 3)
    pygame.draw.circle(ecl, (0, 0, 0), (150, 150), 54)
    return sun, moon, ecl


def make_cloud(seed):
    rnd = random.Random(seed)
    s = pygame.Surface((170, 70), pygame.SRCALPHA)
    for _ in range(14):
        r = rnd.randint(14, 26)
        x, y = rnd.randint(r, 170 - r), rnd.randint(r // 2 + 8, 70 - r // 2)
        pygame.draw.circle(s, (246, 218, 214, 70), (x, y), r)
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


def build_piece(name, theme):
    """Devuelve {clave: superficie} para una pieza del escenario con la paleta dada."""
    if name == "sky":
        return {"sky": make_sky(theme)}
    if name == "far":
        return {"far": make_mountains(1, 150, theme["far"][0], theme["far"][1])}
    if name == "near":
        return {"near": make_mountains(2, 110, theme["near"][0], theme["near"][1])}
    if name == "ground":
        return {"ground": make_ground(theme)}
    cap = make_cap(CAP_W, CAP_H, theme["pipe"], theme["crack"], theme["edge"])
    return {"cyl": make_cylinder(PIPE_W, H, theme["pipe"], theme["crack"]), "cap": cap,
            "cap_flip": pygame.transform.flip(cap, False, True), "spike": theme["spike"]}


PIECES = ("sky", "far", "near", "pipes", "ground")


def make_vignette():
    sw, sh = 36, 64
    s = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for y in range(sh):
        for x in range(sw):
            dx, dy = (x / (sw - 1) - 0.5) * 2, (y / (sh - 1) - 0.5) * 2
            d = min(1.0, math.hypot(dx, dy) / 1.25)
            s.set_at((x, y), (50, 0, 0, int(255 * d ** 2.4)))
    return pygame.transform.smoothscale(s, (W, H))


def make_tux(eyes="open", feet=0):
    """Cuerpo de Tux dibujado con primitivas, 4x supermuestreado (las alas se dibujan aparte).
    eyes: open | blink | scared | dead.  feet: 0 recogidos, 1 colgando."""
    S = 4
    big = pygame.Surface((TUX_W * S, TUX_H * S), pygame.SRCALPHA)

    def E(color, rect, width=0):
        x, y, rw, rh = rect
        pygame.draw.ellipse(big, color, (x * S, (y + PAD) * S, rw * S, rh * S), width * S)

    def L(color, a, b, wd):
        pygame.draw.line(big, color, (a[0] * S, (a[1] + PAD) * S), (b[0] * S, (b[1] + PAD) * S), int(wd * S))

    black, white, orange = (28, 28, 34), (250, 250, 250), (250, 168, 30)
    if feet == 0:
        E(orange, (10, 52, 18, 9))
        E(orange, (26, 52, 18, 9))
    else:
        for cx, ang in ((15, 24), (39, -24)):
            fs = pygame.Surface((18 * S, 9 * S), pygame.SRCALPHA)
            pygame.draw.ellipse(fs, orange, fs.get_rect())
            r = pygame.transform.rotate(fs, ang)
            big.blit(r, (cx * S - r.get_width() // 2, (PAD + 60) * S - r.get_height() // 2))
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
    return pygame.transform.smoothscale(big, (TUX_W, TUX_H))


def make_icon_surface(size=128):
    t = make_tux()
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(s, (120, 190, 232), (size // 2, size // 2), size // 2)
    th = int(size * 0.72)
    t = pygame.transform.smoothscale(t, (int(TUX_W * th / TUX_H), th))
    cx, cy = size // 2, size // 2
    for sx in (-1, 1):  # alas
        w = pygame.Surface((int(size * 0.12), int(size * 0.3)), pygame.SRCALPHA)
        pygame.draw.ellipse(w, (28, 28, 34), w.get_rect())
        w = pygame.transform.rotate(w, -sx * 18)
        s.blit(w, w.get_rect(center=(cx + sx * int(size * 0.27), cy + int(size * 0.03))))
    s.blit(t, ((size - t.get_width()) // 2, (size - t.get_height()) // 2))
    return s


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


def draw_eye(surf, cx, cy, r, op, lx=0.0, ly=0.0, iris=(210, 70, 50), sclera=(246, 240, 230), lid=(60, 26, 30), lw=1):
    """Ojo almendrado con párpado (op: 0 cerrado .. 1 abierto) que mira hacia (lx, ly)."""
    if op <= 0.06:
        return
    h = max(1.0, r * 0.66 * op)
    rect = pygame.Rect(0, 0, max(2, int(2 * r)), max(2, int(2 * h)))
    rect.center = (int(cx), int(cy))
    pygame.draw.ellipse(surf, sclera, rect)
    if r >= 3:
        ir = max(1, int(min(h, r * 0.52)))
        ix, iy = int(cx + lx * (r - ir) * 0.9), int(cy + ly * (h - ir) * 0.9)
        pygame.draw.circle(surf, iris, (ix, iy), ir)
        pygame.draw.circle(surf, (14, 8, 10), (ix, iy), max(1, ir // 2))
    else:
        pygame.draw.circle(surf, iris, (int(cx), int(cy)), max(1, int(lw)))
    pygame.draw.ellipse(surf, lid, rect, lw)


def feather_pts(rx, ry, dx, dy, length, width, smooth):
    """Polígono de una pluma con raíz en (rx, ry) apuntando a (dx, dy)."""
    px, py = -dy, dx
    if smooth:  # forma de lente (ala de pingüino)
        ts = (0.0, 0.18, 0.4, 0.62, 0.82, 1.0)
        hw = [width / 2 * math.sin(math.pi * t) ** 0.6 for t in ts]
        left = [(rx + dx * length * t + px * h, ry + dy * length * t + py * h) for t, h in zip(ts, hw)]
        right = [(rx + dx * length * t - px * h, ry + dy * length * t - py * h) for t, h in zip(ts[-2:0:-1], hw[-2:0:-1])]
        return left + right
    mx, my = rx + dx * length * 0.38, ry + dy * length * 0.38
    return [(rx, ry), (mx + px * width / 2, my + py * width / 2), (rx + dx * length, ry + dy * length),
            (mx - px * width / 2, my - py * width / 2)]


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
        self.clock = pygame.time.Clock()

        self.A = {}
        theme = theme_at(0)
        for name in PIECES:
            self.A.update(build_piece(name, theme))
        self.sun, self.moon, self.ecl = make_orbs()
        self.clouds_img = [make_cloud(i) for i in range(3)]
        self.tux_cache = {}
        self.warm = [(e, f) for e in ("open", "blink", "scared", "dead") for f in (0, 1)]
        self.vignette = make_vignette()
        self.auras = {}
        self.rays = make_rays()
        self.lay_a = pygame.Surface((LW * SS, LW * SS), pygame.SRCALPHA)
        self.lay_b = pygame.Surface((LW * SS, LW * SS), pygame.SRCALPHA)
        self.flash_surf = pygame.Surface((W, H))
        self.flash_surf.fill((255, 255, 255))
        self.font_big = pygame.font.Font(None, 96)
        self.font_mid = pygame.font.Font(None, 44)
        self.font_ban = pygame.font.Font(None, 36)
        self.font_sm = pygame.font.Font(None, 30)
        self.sounds = make_sounds()
        self.flakes = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.5, 1.6)] for _ in range(46)]
        self.locusts = [[random.uniform(0, W), random.uniform(60, GROUND_Y - 40), random.uniform(0, 6.3),
                         random.uniform(150, 240)] for _ in range(60)]
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
        self.pipes = []  # [x, centro_base, puntuado, fase, ojos]
        self.score = 0
        self.u = 0.0  # progreso continuo: gobierna todo el mundo
        self.t = 0.0
        self.pt = 0.0  # tiempo de juego (mueve las columnas)
        self.dead_t = 0.0
        self.shake = 0.0
        self.new_best = False
        self.scroll = 0.0
        self.shown = 0  # último título mostrado
        self.banner_t = 0.0
        self.banner_i = 0
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
        # entorno y Tux generativos: crecen y se acumulan, nunca retroceden
        self.sky_eyes = []
        self.wing_eyes = []
        self.clouds = [[random.uniform(0, W), random.uniform(GROUND_Y - 190, GROUND_Y - 30), random.randrange(3),
                        random.uniform(4, 14)] for _ in range(8)]
        self.built_u = 0.0
        self.rebuild_q = []
        self.rebuild_theme = theme_at(0)
        for name in PIECES:  # vuelve a la paleta inicial
            self.A.update(build_piece(name, self.rebuild_theme))
        for i in range(4):
            self._add_pipe(W + 120 + i * BASE_SPACING)

    def _bounds(self):
        return 60 + self.gap / 2, GROUND_Y - 60 - self.gap / 2

    def _amp_for(self, u):
        return min(40.0, max(0.0, (u - 2.0) * 16.0))

    def _add_pipe(self, x):
        lo, hi = self._bounds()
        m = self._amp_for(self.u)
        prev = self.pipes[-1][1] if self.pipes else (lo + hi) / 2
        c = min(hi - m, max(lo + m, prev + random.uniform(-190, 190)))
        eyes = []
        for _ in range(int(min(4.0, max(0.0, (self.u - 2.2) * 1.3)))):  # columnas con ojos
            eyes.append(dict(dx=random.uniform(-14, 14), off=random.uniform(24, 200), r=random.uniform(5, 10),
                             top=random.random() < 0.5, ph=random.uniform(0, 5), per=random.uniform(3, 6),
                             iris=random.choice(IRIS), born=self.t + random.uniform(0, 1.5)))
        self.pipes.append([x, c, False, random.uniform(0, 6.3), eyes])

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
            if self.u > 1.5:  # plumas que caen de las alas
                for _ in range(int(1 + min(3, self.u))):
                    self.puffs.append([TUX_X + random.uniform(-26, 6), self.y + random.uniform(-6, 10),
                                       random.uniform(-70, -15), random.uniform(-25, 20), 0.9, 0.9,
                                       (240, 244, 255), 3, 90.0, "f"])
            self._play("flap")

    def _play(self, name):
        s = self.sounds.get(name)
        if s:
            s.play()

    def _check_title(self):
        iu = int(self.u)
        if iu > self.shown and iu < len(NAMES):
            self.shown = iu
            self.banner_t, self.banner_i = 3.4, iu
            self._play("level")
            for _ in range(24):
                self.puffs.append([TUX_X, self.y, random.uniform(-140, 140), random.uniform(-150, 40), 0.9, 0.9,
                                   (255, 232, 150), 3, -30.0, "p"])
            if iu >= 2:
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

    # -- generación procedural (acumulativa)
    def _pairs(self):
        return min(5.0, max(0.0, (self.u - 1.2) * 0.9))

    def _nf(self):
        return min(8.0, 1.0 + self.u * 1.7)

    def _grow(self):
        u = self.u
        want = int(min(36.0, max(0.0, (u - 2.0) * 5.5)))
        while len(self.sky_eyes) < want:
            r = random.uniform(7, 20)
            self.sky_eyes.append(dict(x=random.uniform(0, W), y=random.uniform(40, GROUND_Y - 120), r=r,
                                      ph=random.uniform(0, 5), per=random.uniform(3, 6.5), born=self.t,
                                      iris=random.choice(IRIS)))
        want = int(min(40.0, max(0.0, (u - 2.2) * 5.0)))
        pairs_avail = 1 + int(self._pairs())
        while len(self.wing_eyes) < want:
            self.wing_eyes.append(dict(j=random.randrange(pairs_avail), side=random.choice((-1, 1)),
                                       i=random.randrange(int(self._nf())), frac=random.uniform(0.4, 0.88),
                                       r=random.uniform(2.2, 4.2), ph=random.uniform(0, 5), per=random.uniform(3, 6),
                                       born=self.t, iris=random.choice(IRIS)))

    def blink(self, ph, per):
        x = (self.t + ph) % per
        return abs(x - 0.16) / 0.16 if x < 0.32 else 1.0

    # -- ambiente (corre siempre)
    def _update_ambience(self, dt):
        u = self.u
        self.banner_t = max(0.0, self.banner_t - dt)
        self.flash = max(0.0, self.flash - dt * 2.5)
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt)
        if self.bolt_t > 0:
            self.bolt_t -= dt

        # paleta: se reconstruye una pieza por cuadro cuando el progreso cambió lo suficiente
        if self.rebuild_q:
            name = self.rebuild_q.pop(0)
            self.A.update(build_piece(name, self.rebuild_theme))
        elif abs(u - self.built_u) > 0.08:
            self.built_u = u
            self.rebuild_theme = theme_at(u)
            self.rebuild_q = list(PIECES)

        col, (vb, vx), drift = kf(FLAKES, u)
        for f in self.flakes:
            vy = vb + vx * f[2]
            f[1] += vy * dt
            f[0] += (math.sin(self.t * 0.8 + f[1] * 0.02) * 12 + drift) * dt
            if vy > 0 and f[1] > H:
                f[0], f[1] = random.uniform(0, W + 40), -4
            elif vy < 0 and f[1] < -4:
                f[0], f[1] = random.uniform(0, W), H + 4
            f[0] %= W + 40

        for cl in self.clouds:
            cl[0] -= cl[3] * dt
            if cl[0] < -180:
                cl[0] = W + random.uniform(0, 60)
        for e in self.sky_eyes:
            e["x"] -= (3 + e["r"] * 0.35) * dt
            if e["x"] < -30:
                e["x"], e["y"] = W + 30, random.uniform(40, GROUND_Y - 120)

        if u >= 2.4:
            for lc in self.locusts:
                lc[0] -= lc[3] * dt
                lc[1] += math.sin(self.t * 5 + lc[2]) * 40 * dt
                if lc[0] < -10:
                    lc[0], lc[1] = W + random.uniform(10, 80), random.uniform(60, GROUND_Y - 40)
        if u >= 2.6 and self.state != READY:
            self.next_bolt -= dt
            if self.next_bolt <= 0:
                self.strike()
                self.next_bolt = random.uniform(1.0, 2.5) * lerp(3.0, 1.0, ramp(u, 2.6, 5.0))
        if u >= 3.3:
            self.meteor_cd -= dt
            if self.meteor_cd <= 0:
                self.meteor_cd = random.uniform(0.15, 0.4) * lerp(3.0, 1.0, ramp(u, 3.3, 4.2))
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
            self.tux_img(*self.warm.pop(0))

    def tux_img(self, eyes, feet):
        key = (eyes, feet)
        im = self.tux_cache.get(key)
        if im is None:
            im = self.tux_cache[key] = make_tux(eyes, feet)
        return im

    # -- física
    def _target_u(self):
        frac = 0.0
        nxt = next((p for p in self.pipes if not p[2]), None)
        if nxt:  # el progreso también avanza entre columna y columna
            frac = min(1.0, max(0.0, 1 - (nxt[0] - TUX_X) / (BASE_SPACING + 15 * min(self.u, 7.0))))
        return (self.score + frac) / SCORE_PER_U

    def update(self, dt):
        self.t += dt
        self._update_ambience(dt)
        self._update_anim(dt)
        if self.state != READY:
            self._grow()

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
        self.u += (self._target_u() - self.u) * (1 - math.exp(-dt * 0.9))
        self._check_title()
        u = self.u
        self.speed = approach(self.speed, BASE_SPEED + 8 * min(u, 6.0), 25 * dt)
        self.gap = approach(self.gap, BASE_GAP - 4 * min(u, 5.0), 15 * dt)
        self.amp = approach(self.amp, self._amp_for(u), 12 * dt)

        self.vy = min(MAX_FALL, self.vy + GRAVITY * dt)
        self.y += self.vy * dt
        for p in self.pipes:
            p[0] -= self.speed * dt
            if not p[2] and p[0] + PIPE_W / 2 < TUX_X:
                p[2] = True
                self.score += 1
                self._play("score")
        if self.pipes and self.pipes[0][0] + CAP_W / 2 < -10:
            self.pipes.pop(0)
            self._add_pipe(self.pipes[-1][0] + BASE_SPACING + 15 * min(u, 6.0))

        if u >= 0.6:  # estela de destellos dorados
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

    def _look(self, x, y):
        dx, dy = TUX_X - x, self.y - y
        d = max(1.0, math.hypot(dx, dy))
        return dx / d, dy / d

    def _draw_orbs(self, surf):
        u = self.u
        a = ramp(u, 0.3, 1.0) * (1 - ramp(u, 2.2, 3.2))
        if a > 0:
            self.sun.set_alpha(int(255 * a))
            surf.blit(self.sun, (90 - 150, 350 + 70 * ramp(u, 1.0, 3.0) - 150))
        a = ramp(u, 2.2, 3.0) * (1 - ramp(u, 3.6, 4.3))
        if a > 0:
            self.moon.set_alpha(int(255 * a))
            surf.blit(self.moon, (265 - 120, 140 - 120))
        a = ramp(u, 3.3, 4.0)
        if a > 0:
            self.ecl.set_alpha(int(255 * a * (0.85 + 0.15 * math.sin(self.t * 2))))
            surf.blit(self.ecl, (235 - 150, 170 - 150))

    def draw_world(self, surf):
        A, u = self.A, self.u
        surf.blit(A["sky"], (0, 0))
        self._draw_orbs(surf)
        for e in self.sky_eyes:  # ojos en el cielo, se abren y siguen a Tux
            op = min(1.0, (self.t - e["born"]) / 1.5) * self.blink(e["ph"], e["per"])
            lx, ly = self._look(e["x"], e["y"])
            draw_eye(surf, e["x"], e["y"], e["r"], op, lx, ly, e["iris"])
        for key, speed, y in (("far", 6, GROUND_Y - 250), ("near", 18, GROUND_Y - 235)):
            img = A[key]
            iw = img.get_width()
            ox = -((self.t * speed) % iw)
            surf.blit(img, (ox, y))
            surf.blit(img, (ox + iw, y))
            if key == "far":
                ca = ramp(u, 2.4, 4.0) * 0.6
                if ca > 0:
                    for x, cy, k, _ in self.clouds:
                        im = self.clouds_img[k]
                        im.set_alpha(int(255 * ca))
                        surf.blit(im, (x, cy))
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
            for e in p[4]:  # ojos en las columnas
                ey = (top_end - CAP_H - e["off"]) if e["top"] else (bot_start + CAP_H + e["off"])
                if 10 < ey < GROUND_Y - 10:
                    op = min(1.0, max(0.0, (self.t - e["born"]) / 1.0)) * self.blink(e["ph"], e["per"])
                    lx, ly = self._look(x + e["dx"], ey)
                    draw_eye(surf, x + e["dx"], ey, e["r"], op, lx, ly, e["iris"])
        surf.blit(A["ground"], (-self.scroll, GROUND_Y))

    # --- Tux generativo
    def _aura(self, r, alpha):
        key = (r, alpha)
        a = self.auras.get(key)
        if a is None:
            if len(self.auras) > 24:
                self.auras.clear()
            a = self.auras[key] = make_aura(r, alpha)
        return a

    def _T(self, lx, ly, sx, sy):
        """Coordenada local (centro del cuerpo) -> pantalla, con squash y rotación."""
        th = math.radians(self.ang)
        c, s = math.cos(th), math.sin(th)
        lx, ly = lx * sx, ly * sy
        return TUX_X + lx * c - ly * s, self.y + lx * s + ly * c

    def _px(self, x, y):
        return (x - self._ox) * SS, (y - self._oy) * SS

    def _begin(self, layer):
        layer.fill((0, 0, 0, 0))
        self._dst = layer

    def _flush(self, c):
        small = pygame.transform.smoothscale(self._dst, (LW, LW))
        c.blit(small, (self._ox, self._oy))

    def _eye(self, x, y, r, op, iris, look=None):
        lx, ly = look if look else self._look(x, y)
        px, py = self._px(x, y)
        draw_eye(self._dst, px, py, r * SS, op, lx, ly, iris, lw=SS)

    def _rings(self, sx, sy, front):
        """Ruedas con ojos (ofanim): la mitad trasera antes del cuerpo y la delantera después."""
        u, d = self.u, self._dst
        nring = min(4.0, max(0.0, (u - 2.6) * 0.8))
        k = 1
        while nring > k - 1 and k <= 4:
            g = min(1.0, nring - (k - 1))
            a = (30 + 10 * (k - 1)) * g
            b = a * 0.34
            phi = self.t * (0.6 + 0.25 * k) * (1 if k % 2 else -1) + k * 1.3
            cp, sp = math.cos(phi), math.sin(phi)
            col = (255, 226, 120) if front else (170, 130, 60)
            seg = []
            for n in range(41):
                th = n * math.tau / 40
                ex, ey = a * math.cos(th), b * math.sin(th)
                if (math.sin(th) >= 0) == front:
                    seg.append(self._px(*self._T(ex * cp - ey * sp, ex * sp + ey * cp, sx, sy)))
                else:
                    if len(seg) > 1:
                        pygame.draw.lines(d, col, False, seg, 2 * SS)
                    seg = []
            if len(seg) > 1:
                pygame.draw.lines(d, col, False, seg, 2 * SS)
            if u > 3.4:  # los ojos de la rueda
                ne = 3 + k
                for j in range(ne):
                    th = j * math.tau / ne + self.t * (0.9 - 0.2 * k) * (1 if k % 2 else -1)
                    if (math.sin(th) >= 0) != front:
                        continue
                    ex, ey = a * math.cos(th), b * math.sin(th)
                    x, y = self._T(ex * cp - ey * sp, ex * sp + ey * cp, sx, sy)
                    op = ramp(u, 3.3 + 0.12 * j + 0.2 * k, 3.6 + 0.12 * j + 0.2 * k) * g
                    self._eye(x, y, 4.0, op * self.blink(j * 1.1, 4.5), IRIS[(j + k) % 4])
            k += 1

    def _draw_wings(self, sx, sy):
        u, d = self.u, self._dst
        wf = ramp(u, 0.7, 2.6)
        base = mix((28, 28, 34), (250, 250, 255), wf)
        outline = mix((10, 10, 16), (150, 168, 200), wf)
        stain_k = ramp(u, 3.0, 7.0) * 0.6
        pf, nf = self._pairs(), self._nf()
        lmax0 = 22 + 3.6 * min(u, 6.0)
        th = math.radians(self.ang)
        cs, sn = math.cos(th), math.sin(th)
        pos = {}
        for j in range(int(math.ceil(pf)) + 1):
            g = 1.0 if j == 0 else min(1.0, pf - (j - 1))
            if g <= 0:
                continue
            if j == 0:
                ry, shift = -6, 0.0
            elif j % 2:
                ry, shift = -10 - 6 * ((j - 1) // 2), math.radians(24 + 9 * ((j - 1) // 2))
            else:
                ry, shift = 6 + 6 * (j // 2 - 1), -math.radians(26 + 8 * (j // 2 - 1))
            kj = min(1.0, max(0.0, self.wing_k + 0.07 * j * math.sin(self.t * 6 + j * 1.3)))
            alpha = math.radians(lerp(65, -70, kj)) + shift
            nfj = max(1.0, nf - 0.6 * j)
            n = int(math.ceil(nfj))
            lmax = lmax0 * (1 - 0.11 * j) * g
            smooth = nfj < 2.5
            for side in (-1, 1):
                rx, ry2 = self._T(side * 17, ry, sx, sy)
                for i in range(n):
                    sc = min(1.0, nfj - i)
                    ang = alpha + (i - (n - 1) / 2) * 0.21
                    lf = lmax * (0.7 + 0.3 * math.sin(math.pi * (i + 0.5) / n)) * sc
                    ldx, ldy = side * math.cos(ang), -math.sin(ang)
                    dx, dy = ldx * cs - ldy * sn, ldx * sn + ldy * cs
                    col = mix(base, (176, 96, 86), stain_k * (((j * 7 + i * 13 + (side + 1) * 5) % 10) / 10.0))
                    pts = [self._px(*q) for q in feather_pts(rx, ry2, dx, dy, lf, lf * (0.5 if smooth else 0.34), smooth)]
                    pygame.draw.polygon(d, col, pts)
                    pygame.draw.polygon(d, outline, pts, SS)
                    pos[(j, side, i)] = (rx, ry2, dx, dy, lf)
        for e in self.wing_eyes:  # ojos sobre las plumas
            f = pos.get((e["j"], e["side"], e["i"]))
            if not f:
                continue
            rx, ry2, dx, dy, lf = f
            op = min(1.0, (self.t - e["born"]) / 1.2) * self.blink(e["ph"], e["per"])
            self._eye(rx + dx * lf * e["frac"], ry2 + dy * lf * e["frac"], e["r"] + 0.8, op, e["iris"])

    def _draw_halo(self, sx, sy):
        u, d = self.u, self._dst
        a = ramp(u, 1.3, 2.2)
        if a <= 0:
            return
        s = 1 + 0.12 * min(u, 5.0)
        dd = 34 + 3 * math.sin(self.t * 4)
        pulse = 0.6 + 0.4 * math.sin(self.t * 6)
        rw, rh = 14 * s, 5 * s

        def ellipse(scale, cy):
            return [self._px(*self._T(rw * scale * math.cos(n * math.tau / 28), cy + rh * scale * math.sin(n * math.tau / 28), 1, 1))
                    for n in range(28)]
        pygame.draw.polygon(d, (255, 214, 64, int(120 * pulse * a)), ellipse(1.5, -dd))
        pygame.draw.lines(d, (255, 226, 96, int(255 * a)), True, ellipse(1.0, -dd), 3 * SS)
        if u > 2.5:
            pygame.draw.lines(d, (255, 248, 200, int(255 * a)), True, ellipse(0.78, -dd), SS)

    def _draw_stars(self):
        bx, by = self._T(0, -34, 1, 1)
        for i in range(3):
            a = self.t * 5 + i * 2.094
            x, y = bx + math.cos(a) * 20, by + math.sin(a) * 6
            pts = [self._px(x + math.cos(k * math.pi / 4) * (5 if k % 2 == 0 else 2),
                            y + math.sin(k * math.pi / 4) * (5 if k % 2 == 0 else 2)) for k in range(8)]
            pygame.draw.polygon(self._dst, (255, 225, 90), pts)

    def _draw_tux(self, c):
        u = self.u
        playing = self.state == PLAYING
        fall = min(1.0, max(0.0, (self.vy - 300) / 400)) if playing else 0.0
        sx = 1 - 0.14 * self.sq - 0.07 * fall
        sy = 1 + 0.20 * self.sq + 0.10 * fall
        self._ox, self._oy = int(TUX_X - LW / 2), int(self.y - LW / 2)

        ia = ramp(u, 0.3, 1.8)  # aura dorada y rayos
        if ia > 0:
            pulse = 0.75 + 0.25 * math.sin(self.t * 3)
            ra = ramp(u, 3.4, 4.3)
            if ra > 0:
                r = pygame.transform.rotate(self.rays, self.t * 18)
                r.set_alpha(int(255 * pulse * ra))
                c.blit(r, r.get_rect(center=(TUX_X, self.y)))
            rad = int((26 + 13 * min(u, 5.5)) // 4 * 4)
            au = self._aura(rad, 60 + int(14 * min(u, 5.0)))
            au.set_alpha(int(255 * pulse * ia))
            c.blit(au, au.get_rect(center=(TUX_X, self.y)))

        tcol = mix((255, 236, 150), (255, 250, 215), ramp(u, 3.0, 4.5))
        for x, y, _, _, life in self.trail:
            pygame.draw.circle(c, tcol, (int(x), int(y)), 1 + int(life * 5))
        for x, y, _, _, life, maxl, pcol, sz, _, kind in self.puffs:
            f = life / maxl
            if kind == "p":
                pygame.draw.circle(c, pcol, (int(x), int(y)), max(1, int(sz * (0.4 + f))))
            else:  # pluma
                r = (1 - f) * 14
                pygame.draw.line(c, pcol, (x, y), (x + math.cos(r) * 6, y + math.sin(r) * 3), 3)

        # capa trasera: ruedas (mitad de atrás) y alas, supermuestreadas
        self._begin(self.lay_a)
        self._rings(sx, sy, False)
        self._draw_wings(sx, sy)
        self._flush(c)

        if self.state == DEAD:
            eyes = "dead"
        elif self.blink_t > 0:
            eyes = "blink"
        elif playing and self.vy > 420:
            eyes = "scared"
        else:
            eyes = "open"
        feet = 1 if (self.state == DEAD or (playing and self.vy > 150)) else 0
        img = self.tux_img(eyes, feet)
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * sx)), max(1, int(img.get_height() * sy))))
        img = pygame.transform.rotozoom(img, -self.ang, 1.0)
        c.blit(img, img.get_rect(center=(TUX_X, self.y - TUX_OFF)))

        # capa delantera: ojos del cuerpo, ruedas (mitad de adelante), aureola, estrellas
        self._begin(self.lay_b)
        lk = (1.0, max(-1.0, min(1.0, self.vy / 600)))
        for ex, ey, r, ut in BODY_EYES:
            op = ramp(u, ut, ut + 0.3)
            if op > 0 and self.state != DEAD:
                x, y = self._T(ex, ey, sx, sy)
                self._eye(x, y, r, op * self.blink(ex * 0.37 + ey, 4.2), IRIS[(int(ex) + 4) % 4], lk)
        self._rings(sx, sy, True)
        self._draw_halo(sx, sy)
        if self.state == DEAD and self.landed:
            self._draw_stars()
        self._flush(c)

    def draw(self):
        c = self.canvas
        u = self.u
        self.draw_world(c)

        if u >= 2.4:  # langostas
            n = int(min(60, (u - 2.4) * 14))
            for x, y, ph, _ in self.locusts[:n]:
                fl = 3 if int(self.t * 22 + ph * 3) % 2 else 1
                pygame.draw.ellipse(c, (60, 34, 16), (x, y, 6, 3))
                pygame.draw.line(c, (140, 100, 50), (x + 2, y), (x, y - fl), 1)
        for mx, my, vx, vy in self.meteors:  # lluvia de fuego
            pygame.draw.line(c, (255, 140, 40), (mx, my), (mx - vx * 0.09, my - vy * 0.09), 4)
            pygame.draw.line(c, (255, 220, 140), (mx, my), (mx - vx * 0.04, my - vy * 0.04), 2)
            pygame.draw.circle(c, (255, 250, 220), (int(mx), int(my)), 3)

        self._draw_tux(c)

        col, _, _ = kf(FLAKES, u)
        for fx, fy, sz in self.flakes:
            pygame.draw.circle(c, col, (int(fx), int(fy)), 1 + int(sz > 1.1))

        if self.bolt_t > 0 and self.bolt:
            pygame.draw.lines(c, (190, 190, 255), False, self.bolt, 7)
            pygame.draw.lines(c, (255, 255, 255), False, self.bolt, 3)
        if self.flash > 0:
            self.flash_surf.set_alpha(int(170 * self.flash))
            c.blit(self.flash_surf, (0, 0))

        vig = min(235.0, max(0.0, (u - 1.5) * 92))
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

    def _draw_banner(self, c):
        a = min(1.0, self.banner_t / 0.5, (3.4 - self.banner_t) / 0.4)
        s = pygame.Surface((W, 110), pygame.SRCALPHA)
        name, sub, _ = NAMES[self.banner_i]
        self.text(s, f"NIVEL {self.banner_i + 1}", self.font_sm, (W // 2, 16), (255, 210, 120))
        self.text(s, name, self.font_ban, (W // 2, 48))
        self.text(s, sub, self.font_sm, (W // 2, 86), (235, 220, 210))
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
            self.text(c, NAMES[min(int(self.u), len(NAMES) - 1)][2], self.font_mid, (W // 2, 188), (200, 60, 50))
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
    try:
        pygame.display.init()
    except pygame.error as e:
        sys.exit(f"Tux Flap no pudo abrir la pantalla: {e}\n"
                 "¿Estás dentro de una sesión gráfica? Prueba con SDL_VIDEODRIVER=wayland o SDL_VIDEODRIVER=x11.")
    Game(fs).run()


if __name__ == "__main__":
    main()
