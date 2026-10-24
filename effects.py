# effects.py - particles, clouds, roadside scenery and speed lines (all drawn with shapes).
import math
import random
import pygame
import settings as S
import terrain


# --------------------------------------------------------------------------
# Particles (dust, exhaust smoke)
# --------------------------------------------------------------------------
class ParticleSystem:
    """Holds every live puff of dust/smoke; each one moves, grows and fades out."""

    def __init__(self, limit=250):
        self.items = []          # [x, y, vx, vy, age, life, size0, size1, colour, alpha, gravity]
        self.limit = limit       # cap so slow PCs never choke
        self.layer = None        # transparent surface the puffs are drawn on

    def emit(self, x, y, vx, vy, life, size0, size1, colour, alpha=150, gravity=0.0):
        """Spawn one particle in world coordinates (gravity > 0 falls, < 0 rises)."""
        if len(self.items) >= self.limit:
            self.items.pop(0)                       # drop the oldest
        self.items.append([x, y, vx, vy, 0.0, life, size0, size1, colour, alpha, gravity])

    def clear(self):
        """Remove all particles (used on restart)."""
        self.items.clear()

    def update(self, dt):
        """Move every particle, age it and delete the ones that expired."""
        alive = []
        for p in self.items:
            p[4] += dt
            if p[4] < p[5]:
                p[3] += p[10] * dt                  # gravity changes vertical speed
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                alive.append(p)
        self.items = alive

    def draw(self, surf, camera_x):
        """Draw all particles as fading circles, shifted by the camera."""
        if self.layer is None or self.layer.get_size() != surf.get_size():
            self.layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        self.layer.fill((0, 0, 0, 0))
        for x, y, _, _, age, life, s0, s1, colour, alpha, _ in self.items:
            t = age / life                          # 0 -> 1 over the particle's life
            size = max(1, int(s0 + (s1 - s0) * t))  # grows
            a = int(alpha * (1 - t))                # fades
            pygame.draw.circle(self.layer, (*colour, a), (int(x - camera_x), int(y)), size)
        surf.blit(self.layer, (0, 0))


# --------------------------------------------------------------------------
# Sky
# --------------------------------------------------------------------------
class Clouds:
    """Slow, hazy clouds that drift on their own and also parallax with the camera."""

    def __init__(self):
        rng = random.Random(3)
        self.shapes = [self.make_cloud(rng) for _ in range(3)]
        self.layout = [(rng.randint(0, S.WIDTH + 400), rng.randint(30, 190),
                        rng.randint(0, 2), rng.uniform(6, 14)) for _ in range(6)]

    @staticmethod
    def make_cloud(rng):
        """Build one cloud picture from overlapping translucent circles."""
        surf = pygame.Surface((170, 64), pygame.SRCALPHA)
        for k in range(6):
            pygame.draw.circle(surf, (255, 250, 240, 170),
                               (34 + k * 20 + rng.randint(-5, 5), 38 + rng.randint(-8, 8)),
                               rng.randint(14, 24))
        return surf

    def draw(self, surf, cam_x, t):
        """Blit every cloud, wrapping around so the sky never empties."""
        span = S.WIDTH + 400
        for base, y, shape, speed in self.layout:
            x = (base - cam_x * 0.08 + t * speed) % span - 200
            surf.blit(self.shapes[shape], (x, y))


# --------------------------------------------------------------------------
# Roadside scenery (poles with flags, swaying trees, chai stalls)
# --------------------------------------------------------------------------
class Scenery:
    """Procedurally places roadside props for the current map; the same world x always gives the same prop."""
    CELL = 260   # one prop per 260 px of world

    def __init__(self):
        """Create the font used on billboards and a cache of rendered billboard texts."""
        self.font = pygame.font.SysFont("arial", 20, bold=True)
        self.texts = {}

    def draw(self, surf, cam_x, t):
        """Draw the props visible on screen, based on a seeded random per world cell."""
        m = terrain.current()
        first = int(cam_x // self.CELL) - 2
        last = int((cam_x + S.WIDTH) // self.CELL) + 2
        for i in range(first, last + 1):
            rng = random.Random(i * 7919 + m["seed"])      # same cell + map -> same prop every frame
            kind = rng.choice(m["scenery"])
            wx = i * self.CELL + rng.randint(20, 200)
            x, y = wx - cam_x, terrain.get_height(wx) + 3
            if kind == "pole":
                self.draw_pole(surf, x, y, t)
            elif kind == "tree":
                self.draw_tree(surf, x, y, t, wx * 0.013)
            elif kind == "stall":
                self.draw_stall(surf, x, y, t)
            elif kind == "pillar":
                self.draw_pillar(surf, x, y)
            elif kind == "crane":
                self.draw_crane(surf, x, y, t)
            elif kind == "billboard":
                self.draw_billboard(surf, x, y, rng.choice(m["billboards"]), rng.randint(0, 3))
            elif kind == "laundry":
                self.draw_laundry(surf, x, y, t)
            elif kind == "bridge":
                self.draw_bridge(surf, x, y)

    @staticmethod
    def draw_pole(surf, x, y, t):
        """Electric pole with a flag whose columns ripple like cloth in the wind."""
        wood = (60, 50, 45)
        pygame.draw.line(surf, wood, (x, y), (x, y - 120), 5)
        pygame.draw.line(surf, wood, (x - 18, y - 108), (x + 18, y - 108), 4)
        for dx in (-18, 18):
            pygame.draw.circle(surf, (205, 205, 205), (x + dx, y - 110), 3)
        pygame.draw.line(surf, wood, (x, y - 120), (x, y - 152), 2)
        for i in range(9):                           # one thin column per step
            wave = math.sin(t * 6 + i * 0.7) * (0.5 + i * 0.35)
            colour = S.WHITE if i < 2 else S.PK_GREEN
            pygame.draw.rect(surf, colour, (x + 2 + i * 4, y - 150 + wave, 4, 17))

    @staticmethod
    def draw_tree(surf, x, y, t, phase):
        """Tree whose leafy top sways gently left and right."""
        sway = math.sin(t * 1.4 + phase) * 3
        pygame.draw.line(surf, (92, 64, 40), (x, y), (x + sway * 0.3, y - 55), 7)
        for dx, dy, r, col in ((0, -72, 25, (40, 110, 50)), (-17, -58, 18, (36, 100, 46)),
                               (17, -58, 18, (36, 100, 46)), (-4, -78, 12, (56, 132, 62))):
            pygame.draw.circle(surf, col, (int(x + dx + sway), int(y + dy)), r)

    @staticmethod
    def draw_stall(surf, x, y, t):
        """Chai stall with a striped awning and steam rising from the kettle."""
        pygame.draw.rect(surf, (110, 78, 50), (x - 30, y - 34, 60, 34))
        pygame.draw.rect(surf, (80, 55, 35), (x - 30, y - 34, 60, 5))
        for px in (-32, 32):
            pygame.draw.line(surf, (70, 50, 35), (x + px, y), (x + px, y - 66), 3)
        for i in range(6):                           # alternating awning stripes
            colour = S.RED if i % 2 == 0 else S.WHITE
            pygame.draw.polygon(surf, colour, [(x - 30 + i * 10, y - 66), (x - 20 + i * 10, y - 66),
                                               (x - 24 + i * 12, y - 50), (x - 36 + i * 12, y - 50)])
        pygame.draw.circle(surf, (150, 150, 155), (x + 10, y - 41), 7)
        for k in range(3):                           # three steam puffs at different heights
            ph = (t * 0.8 + k / 3) % 1
            pygame.draw.circle(surf, (245, 240, 230),
                               (int(x + 10 + math.sin(ph * 6 + k) * 4), int(y - 50 - ph * 28)),
                               int(2 + ph * 3))

    @staticmethod
    def draw_pillar(surf, x, y):
        """Unfinished concrete metro pillar with rusty steel bars sticking out of the top."""
        pygame.draw.rect(surf, (150, 150, 148), (x - 22, y - 180, 44, 180))
        pygame.draw.rect(surf, (118, 118, 116), (x + 8, y - 180, 14, 180))
        pygame.draw.rect(surf, (160, 160, 158), (x - 46, y - 198, 92, 20))
        for dx in range(-36, 40, 12):
            pygame.draw.line(surf, (140, 80, 40), (x + dx, y - 198), (x + dx, y - 222), 2)
        pygame.draw.rect(surf, S.MARIGOLD, (x - 22, y - 26, 44, 10))

    @staticmethod
    def draw_crane(surf, x, y, t):
        """Tower crane with a swaying jib and a hanging hook."""
        gold = (230, 180, 30)
        pygame.draw.rect(surf, gold, (x - 7, y - 220, 14, 220), 2)
        for k in range(0, 220, 22):                  # lattice cross bars
            pygame.draw.line(surf, gold, (x - 7, y - k), (x + 7, y - k - 22), 2)
        sway = math.sin(t * 0.6 + x * 0.01) * 6
        pygame.draw.line(surf, gold, (x - 60, y - 222), (x + 120 + sway, y - 222), 5)
        pygame.draw.line(surf, gold, (x, y - 250), (x + 120 + sway, y - 222), 2)
        pygame.draw.line(surf, gold, (x, y - 250), (x - 60, y - 222), 2)
        pygame.draw.line(surf, (60, 60, 60), (x + 90 + sway, y - 222), (x + 90 + sway * 1.5, y - 160), 2)
        pygame.draw.rect(surf, (200, 60, 40), (x + 82 + sway * 1.5, y - 160, 16, 12))

    def draw_billboard(self, surf, x, y, text, colour_idx):
        """Advertising board on two posts."""
        cols = [(200, 40, 40), (30, 120, 90), (40, 90, 170), (235, 170, 30)]
        for dx in (-44, 44):
            pygame.draw.rect(surf, (70, 70, 74), (x + dx - 3, y - 120, 6, 120))
        board = pygame.Rect(0, 0, 140, 60)
        board.midbottom = (x, y - 100)
        pygame.draw.rect(surf, cols[colour_idx], board, border_radius=4)
        pygame.draw.rect(surf, (240, 240, 235), board, 3, border_radius=4)
        if text not in self.texts:
            self.texts[text] = self.font.render(text, True, S.WHITE)
        img = self.texts[text]
        if img.get_width() > 124:
            img = pygame.transform.smoothscale(img, (124, int(img.get_height() * 124 / img.get_width())))
        surf.blit(img, img.get_rect(center=board.center))

    @staticmethod
    def draw_laundry(surf, x, y, t):
        """Washing line between two poles with clothes swaying in the breeze (Lyari lanes)."""
        wood = (70, 55, 45)
        for dx in (-75, 75):
            pygame.draw.line(surf, wood, (x + dx, y), (x + dx, y - 100), 4)
        pts = [(x - 75 + i * 15, y - 98 + 14 * math.sin(math.pi * i / 10)) for i in range(11)]
        pygame.draw.lines(surf, (40, 40, 40), False, pts, 1)
        cols = [(220, 60, 60), (240, 240, 235), (60, 130, 200), (240, 190, 40), (60, 160, 90), (200, 90, 160)]
        for i in range(6):
            px, py = pts[i + 2]
            sway = math.sin(t * 2.2 + i) * 3
            pygame.draw.polygon(surf, cols[i], [(px - 7, py), (px + 7, py), (px + 7 + sway, py + 24 + (i % 3) * 6),
                                                (px - 7 + sway, py + 24 + (i % 3) * 6)])

    @staticmethod
    def draw_bridge(surf, x, y):
        """Steel pedestrian overhead bridge with stairs on both sides (Shahrah-e-Faisal)."""
        steel, dark = (120, 125, 135), (60, 62, 70)
        for dx in (-110, 110):
            pygame.draw.rect(surf, steel, (x + dx - 6, y - 160, 12, 160))
        pygame.draw.rect(surf, steel, (x - 130, y - 168, 260, 12))
        pygame.draw.line(surf, dark, (x - 130, y - 205), (x + 130, y - 205), 3)
        for i in range(-130, 131, 26):
            pygame.draw.line(surf, dark, (x + i, y - 205), (x + i, y - 168), 2)
        for sgn in (-1, 1):
            pygame.draw.line(surf, steel, (x + sgn * 130, y - 160), (x + sgn * 190, y), 4)
            pygame.draw.line(surf, dark, (x + sgn * 130, y - 200), (x + sgn * 190, y - 40), 2)


# --------------------------------------------------------------------------
# Speed feeling
# --------------------------------------------------------------------------
def draw_speed_lines(surf, speed_frac):
    """Draw random horizontal streaks when going fast; more streaks the faster you go."""
    if speed_frac < 0.6:
        return
    count = int((speed_frac - 0.6) * 30)
    for _ in range(count):
        y = random.randint(60, S.HEIGHT - 140)
        x = random.randint(0, S.WIDTH)
        pygame.draw.line(surf, (255, 255, 255), (x, y), (x - random.randint(30, 80), y), 1)
