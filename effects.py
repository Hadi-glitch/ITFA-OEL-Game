# effects.py - particles, clouds, roadside scenery, speed lines, and 3D visual effects.
import math
import random
import pygame
import settings as S
import terrain


# --------------------------------------------------------------------------
# Particles (dust, exhaust smoke) - enhanced with glow
# --------------------------------------------------------------------------
class ParticleSystem:
    """Holds every live puff of dust/smoke; each one moves, grows and fades out."""

    def __init__(self, limit=300):
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
        """Draw all particles as fading circles with soft edges, shifted by the camera."""
        if self.layer is None or self.layer.get_size() != surf.get_size():
            self.layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        self.layer.fill((0, 0, 0, 0))
        for x, y, _, _, age, life, s0, s1, colour, alpha, _ in self.items:
            t = age / life                          # 0 -> 1 over the particle's life
            size = max(1, int(s0 + (s1 - s0) * t))  # grows
            a = int(alpha * (1 - t))                # fades
            sx, sy = int(x - camera_x), int(y)
            if size > 3:
                # Soft glow ring for larger particles
                pygame.draw.circle(self.layer, (*colour, max(0, a // 3)), (sx, sy), size + 2)
            pygame.draw.circle(self.layer, (*colour, a), (sx, sy), size)
            # Inner highlight for 3D depth
            if size > 4 and a > 40:
                hl = tuple(min(255, c + 60) for c in colour)
                pygame.draw.circle(self.layer, (*hl, a // 2), (sx - size // 4, sy - size // 4), max(1, size // 3))
        surf.blit(self.layer, (0, 0))


# --------------------------------------------------------------------------
# Sky
# --------------------------------------------------------------------------
class Clouds:
    """Slow, hazy clouds that drift on their own and also parallax with the camera."""

    def __init__(self):
        rng = random.Random(3)
        self.shapes = [self.make_cloud(rng) for _ in range(4)]
        self.layout = [(rng.randint(0, S.WIDTH + 400), rng.randint(30, 190),
                        rng.randint(0, 3), rng.uniform(6, 14)) for _ in range(8)]

    @staticmethod
    def make_cloud(rng):
        """Build one cloud picture from overlapping translucent circles with 3D shading."""
        surf = pygame.Surface((200, 80), pygame.SRCALPHA)
        # Shadow layer
        for k in range(7):
            pygame.draw.circle(surf, (180, 170, 155, 50),
                               (38 + k * 22 + rng.randint(-5, 5), 48 + rng.randint(-6, 6)),
                               rng.randint(16, 28))
        # Main cloud body
        for k in range(7):
            r = rng.randint(14, 26)
            cx, cy = 34 + k * 22 + rng.randint(-5, 5), 38 + rng.randint(-8, 8)
            pygame.draw.circle(surf, (255, 252, 245, 170), (cx, cy), r)
            # Top highlight for 3D effect
            pygame.draw.circle(surf, (255, 255, 255, 80), (cx - 2, cy - 3), max(4, r - 6))
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
        wood_hi = (80, 68, 58)
        pygame.draw.line(surf, wood, (x, y), (x, y - 120), 5)
        pygame.draw.line(surf, wood_hi, (x - 1, y), (x - 1, y - 120), 2)   # highlight edge
        pygame.draw.line(surf, wood, (x - 18, y - 108), (x + 18, y - 108), 4)
        for dx in (-18, 18):
            pygame.draw.circle(surf, (225, 225, 225), (x + dx, y - 110), 4)
            pygame.draw.circle(surf, (205, 205, 205), (x + dx, y - 110), 3)
        pygame.draw.line(surf, wood, (x, y - 120), (x, y - 152), 2)
        for i in range(9):                           # one thin column per step
            wave = math.sin(t * 6 + i * 0.7) * (0.5 + i * 0.35)
            colour = S.WHITE if i < 2 else S.PK_GREEN
            pygame.draw.rect(surf, colour, (x + 2 + i * 4, y - 150 + wave, 4, 17))

    @staticmethod
    def draw_tree(surf, x, y, t, phase):
        """Tree whose leafy top sways gently left and right with 3D shading."""
        sway = math.sin(t * 1.4 + phase) * 3
        # Trunk with highlight
        pygame.draw.line(surf, (72, 50, 30), (x + 2, y), (x + 2 + sway * 0.3, y - 55), 8)
        pygame.draw.line(surf, (92, 64, 40), (x, y), (x + sway * 0.3, y - 55), 7)
        # Shadow layer of foliage
        for dx, dy, r in ((2, -70, 26), (-15, -56, 19), (19, -56, 19)):
            pygame.draw.circle(surf, (25, 70, 30), (int(x + dx + sway + 2), int(y + dy + 2)), r)
        # Main foliage
        for dx, dy, r, col in ((0, -72, 25, (40, 110, 50)), (-17, -58, 18, (36, 100, 46)),
                               (17, -58, 18, (36, 100, 46)), (-4, -78, 12, (56, 132, 62))):
            pygame.draw.circle(surf, col, (int(x + dx + sway), int(y + dy)), r)
        # 3D highlight on top of foliage
        for dx, dy, r in ((-2, -76, 10), (-19, -62, 8)):
            pygame.draw.circle(surf, (70, 145, 70), (int(x + dx + sway), int(y + dy)), r)

    @staticmethod
    def draw_stall(surf, x, y, t):
        """Chai stall with a striped awning, shadow, and steam rising from the kettle."""
        # Shadow under stall
        shadow = pygame.Surface((80, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 50), shadow.get_rect())
        surf.blit(shadow, (x - 40, y - 2))
        # Counter with 3D depth
        pygame.draw.rect(surf, (90, 60, 35), (x - 30, y - 34, 60, 34))   # dark side
        pygame.draw.rect(surf, (110, 78, 50), (x - 28, y - 34, 56, 32))  # front face
        pygame.draw.rect(surf, (125, 92, 60), (x - 28, y - 34, 56, 5))   # top surface highlight
        for px in (-32, 32):
            pygame.draw.line(surf, (70, 50, 35), (x + px, y), (x + px, y - 66), 3)
        for i in range(6):                           # alternating awning stripes
            colour = S.RED if i % 2 == 0 else S.WHITE
            pygame.draw.polygon(surf, colour, [(x - 30 + i * 10, y - 66), (x - 20 + i * 10, y - 66),
                                               (x - 24 + i * 12, y - 50), (x - 36 + i * 12, y - 50)])
        # Awning fringe
        for i in range(12):
            bx = x - 32 + i * 5
            pygame.draw.line(surf, S.MARIGOLD, (bx, y - 50), (bx, y - 46), 1)
        pygame.draw.circle(surf, (160, 160, 165), (x + 10, y - 41), 7)
        pygame.draw.circle(surf, (180, 180, 185), (x + 8, y - 43), 3)    # kettle shine
        for k in range(3):                           # three steam puffs at different heights
            ph = (t * 0.8 + k / 3) % 1
            r = int(2 + ph * 3)
            alpha = int(140 * (1 - ph))
            steam = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(steam, (245, 240, 230, alpha), (r * 2, r * 2), r * 2)
            surf.blit(steam, (int(x + 10 + math.sin(ph * 6 + k) * 4) - r * 2,
                              int(y - 50 - ph * 28) - r * 2))

    @staticmethod
    def draw_pillar(surf, x, y):
        """Unfinished concrete metro pillar with rusty steel bars sticking out of the top."""
        # Shadow
        shadow = pygame.Surface((60, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 40), shadow.get_rect())
        surf.blit(shadow, (x - 30, y - 4))
        # Pillar body with 3D shading
        pygame.draw.rect(surf, (130, 130, 128), (x - 22, y - 180, 44, 180))  # dark side
        pygame.draw.rect(surf, (150, 150, 148), (x - 20, y - 180, 28, 180))  # lit face
        pygame.draw.rect(surf, (165, 165, 163), (x - 20, y - 180, 8, 180))   # highlight edge
        pygame.draw.rect(surf, (118, 118, 116), (x + 8, y - 180, 14, 180))
        pygame.draw.rect(surf, (160, 160, 158), (x - 46, y - 198, 92, 20))
        pygame.draw.rect(surf, (175, 175, 173), (x - 46, y - 198, 92, 6))    # top highlight
        for dx in range(-36, 40, 12):
            pygame.draw.line(surf, (140, 80, 40), (x + dx, y - 198), (x + dx, y - 222), 2)
        pygame.draw.rect(surf, S.MARIGOLD, (x - 22, y - 26, 44, 10))

    @staticmethod
    def draw_crane(surf, x, y, t):
        """Tower crane with a swaying jib and a hanging hook."""
        gold = (230, 180, 30)
        gold_hi = (250, 210, 60)
        pygame.draw.rect(surf, gold, (x - 7, y - 220, 14, 220), 2)
        for k in range(0, 220, 22):                  # lattice cross bars
            pygame.draw.line(surf, gold, (x - 7, y - k), (x + 7, y - k - 22), 2)
        sway = math.sin(t * 0.6 + x * 0.01) * 6
        pygame.draw.line(surf, gold, (x - 60, y - 222), (x + 120 + sway, y - 222), 5)
        pygame.draw.line(surf, gold_hi, (x - 60, y - 224), (x + 120 + sway, y - 224), 2)  # top highlight
        pygame.draw.line(surf, gold, (x, y - 250), (x + 120 + sway, y - 222), 2)
        pygame.draw.line(surf, gold, (x, y - 250), (x - 60, y - 222), 2)
        pygame.draw.line(surf, (60, 60, 60), (x + 90 + sway, y - 222), (x + 90 + sway * 1.5, y - 160), 2)
        pygame.draw.rect(surf, (200, 60, 40), (x + 82 + sway * 1.5, y - 160, 16, 12))

    def draw_billboard(self, surf, x, y, text, colour_idx):
        """Advertising board on two posts with 3D frame."""
        cols = [(200, 40, 40), (30, 120, 90), (40, 90, 170), (235, 170, 30)]
        for dx in (-44, 44):
            pygame.draw.rect(surf, (80, 80, 84), (x + dx - 3, y - 120, 6, 120))
            pygame.draw.rect(surf, (70, 70, 74), (x + dx - 2, y - 120, 4, 120))
        board = pygame.Rect(0, 0, 140, 60)
        board.midbottom = (x, y - 100)
        # Shadow behind board
        pygame.draw.rect(surf, (0, 0, 0, 60) if len(cols[colour_idx]) == 3 else (30, 30, 30),
                         board.move(3, 3), border_radius=4)
        pygame.draw.rect(surf, cols[colour_idx], board, border_radius=4)
        # 3D border effect
        pygame.draw.rect(surf, tuple(min(255, c + 40) for c in cols[colour_idx]),
                         (board.left, board.top, board.width, 3), border_radius=4)
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
            cloth_col = cols[i]
            # Cloth with slight 3D shading
            points = [(px - 7, py), (px + 7, py), (px + 7 + sway, py + 24 + (i % 3) * 6),
                      (px - 7 + sway, py + 24 + (i % 3) * 6)]
            pygame.draw.polygon(surf, cloth_col, points)
            # Shadow fold line
            darker = tuple(max(0, c - 40) for c in cloth_col)
            mid_y = py + 12 + (i % 3) * 3
            pygame.draw.line(surf, darker, (px - 3 + sway * 0.5, mid_y), (px + 3 + sway * 0.5, mid_y), 1)

    @staticmethod
    def draw_bridge(surf, x, y):
        """Steel pedestrian overhead bridge with stairs on both sides (Shahrah-e-Faisal)."""
        steel, dark = (120, 125, 135), (60, 62, 70)
        steel_hi = (145, 150, 160)
        for dx in (-110, 110):
            pygame.draw.rect(surf, steel, (x + dx - 6, y - 160, 12, 160))
            pygame.draw.rect(surf, steel_hi, (x + dx - 6, y - 160, 4, 160))  # highlight
        pygame.draw.rect(surf, steel, (x - 130, y - 168, 260, 12))
        pygame.draw.rect(surf, steel_hi, (x - 130, y - 168, 260, 4))  # top highlight
        pygame.draw.line(surf, dark, (x - 130, y - 205), (x + 130, y - 205), 3)
        for i in range(-130, 131, 26):
            pygame.draw.line(surf, dark, (x + i, y - 205), (x + i, y - 168), 2)
        for sgn in (-1, 1):
            pygame.draw.line(surf, steel, (x + sgn * 130, y - 160), (x + sgn * 190, y), 4)
            pygame.draw.line(surf, dark, (x + sgn * 130, y - 200), (x + sgn * 190, y - 40), 2)


# --------------------------------------------------------------------------
# Speed feeling - enhanced with motion blur effect
# --------------------------------------------------------------------------
_speed_layer = None


def draw_speed_lines(surf, speed_frac):
    """Disabled: speed visual streaks removed."""
    pass


# --------------------------------------------------------------------------
# Screen flash (brief colour burst on powerup pickup or milestone)
# --------------------------------------------------------------------------
class ScreenFlash:
    """Brief full-screen colour flash that fades out quickly."""

    def __init__(self):
        self.surface = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        self.alpha = 0.0
        self.color = (255, 255, 255)

    def trigger(self, color=(255, 255, 255), strength=80):
        """Start a flash with the given colour and initial alpha."""
        self.color = color
        self.alpha = strength

    def update(self, dt):
        """Fade the flash toward zero."""
        if self.alpha > 0:
            self.alpha = max(0.0, self.alpha - 300 * dt)

    def draw(self, surf):
        """Blit the flash if it is still visible."""
        if self.alpha > 1:
            self.surface.fill((*self.color, int(self.alpha)))
            surf.blit(self.surface, (0, 0))


# --------------------------------------------------------------------------
# Vignette (3D depth dark edges around the screen) - enhanced
# --------------------------------------------------------------------------
_vignette = None


def draw_vignette(surf):
    """Draw a pre-rendered dark vignette around the screen edges - enhanced for 3D depth."""
    global _vignette
    if _vignette is None:
        _vignette = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        for i in range(60):
            alpha = int(45 * (1 - i / 60) ** 2.5)
            rect = pygame.Rect(i, i, S.WIDTH - 2 * i, S.HEIGHT - 2 * i)
            pygame.draw.rect(_vignette, (0, 0, 0, alpha), rect, 1)
        # Extra darkening at bottom corners for ground depth
        for i in range(40):
            alpha = int(25 * (1 - i / 40) ** 2)
            pygame.draw.rect(_vignette, (0, 0, 0, alpha),
                             (0, S.HEIGHT - 40 + i, S.WIDTH, 1))
    surf.blit(_vignette, (0, 0))


# --------------------------------------------------------------------------
# Low-health warning (red pulse at screen edges)
# --------------------------------------------------------------------------
_health_warn = None


def draw_low_health_warning(surf, health_frac, t):
    """Pulse red at screen edges when health is below 25%."""
    global _health_warn
    if health_frac > 0.25:
        return
    if _health_warn is None:
        _health_warn = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    alpha = int(55 * pulse * (1 - health_frac / 0.25))
    _health_warn.fill((0, 0, 0, 0))
    bw = 28
    pygame.draw.rect(_health_warn, (200, 20, 20, alpha), (0, 0, S.WIDTH, bw))
    pygame.draw.rect(_health_warn, (200, 20, 20, alpha), (0, S.HEIGHT - bw, S.WIDTH, bw))
    pygame.draw.rect(_health_warn, (200, 20, 20, alpha), (0, 0, bw, S.HEIGHT))
    pygame.draw.rect(_health_warn, (200, 20, 20, alpha), (S.WIDTH - bw, 0, bw, S.HEIGHT))
    surf.blit(_health_warn, (0, 0))


# --------------------------------------------------------------------------
# 3D Road depth overlay (drawn behind the vehicle)
# --------------------------------------------------------------------------
_road_depth = None


def draw_road_depth(surf, cam, time_val):
    """Draw a subtle 3D depth effect on the road: shadow gradient and specular highlight strip."""
    global _road_depth
    if _road_depth is None or _road_depth.get_size() != surf.get_size():
        _road_depth = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    _road_depth.fill((0, 0, 0, 0))

    # Road surface specular highlight (moving with camera for realism)
    for sx in range(0, S.WIDTH, 6):
        wx = sx + cam
        y = terrain.get_height(wx)
        # Subtle highlight on road surface
        shimmer = 8 + 4 * math.sin(wx * 0.02 + time_val * 0.5)
        alpha = int(shimmer)
        pygame.draw.line(_road_depth, (255, 255, 240, alpha), (sx, int(y) + 12), (sx, int(y) + 18), 3)

    surf.blit(_road_depth, (0, 0))


# --------------------------------------------------------------------------
# Heat shimmer effect for hot maps
# --------------------------------------------------------------------------
_heat_layer = None


def draw_heat_shimmer(surf, t, intensity=0.5):
    """Subtle heat shimmer above the road for a hot atmosphere feel."""
    global _heat_layer
    if _heat_layer is None or _heat_layer.get_size() != surf.get_size():
        _heat_layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    _heat_layer.fill((0, 0, 0, 0))
    for x in range(0, S.WIDTH, 8):
        y_base = S.HEIGHT - 180
        wave = math.sin(x * 0.03 + t * 2) * 2 * intensity
        alpha = int(15 * intensity)
        pygame.draw.line(_heat_layer, (255, 240, 200, alpha),
                         (x, int(y_base + wave)), (x, int(y_base + wave + 6)), 2)
    surf.blit(_heat_layer, (0, 0))
