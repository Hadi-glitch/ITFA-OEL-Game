# powerups.py - road powerups: definitions, drawing and active-effect tracking.
import math
import pygame
import settings as S


# ---- Powerup types ----
# Each powerup: id, display name, colour, duration (seconds), spawn weight.
POWERUPS = [
    dict(id="speed_boost",  name="SPEED",  color=(0, 200, 255),  duration=5.0, weight=3),
    dict(id="health_regen", name="REGEN",  color=(255, 70, 110), duration=4.0, weight=3),
    dict(id="shield",       name="SHIELD", color=(255, 210, 40), duration=4.0, weight=2),
    dict(id="magnet",       name="MAGNET", color=(180, 80, 255), duration=6.0, weight=2),
    dict(id="double_coins", name="2x",     color=(255, 160, 30), duration=8.0, weight=2),
]
BY_ID = {p["id"]: p for p in POWERUPS}

# Upgrade tiers: each powerup has 3 levels of stats.
UPGRADES = {
    "speed_boost": [
        dict(duration=5.0,  mult=1.4,  desc="1.4x speed for 5s"),
        dict(duration=7.0,  mult=1.5,  desc="1.5x speed for 7s"),
        dict(duration=9.0,  mult=1.6,  desc="1.6x speed for 9s"),
    ],
    "health_regen": [
        dict(duration=4.0,  total=30,  desc="Restore 30 HP in 4s"),
        dict(duration=5.0,  total=50,  desc="Restore 50 HP in 5s"),
        dict(duration=6.0,  total=70,  desc="Restore 70 HP in 6s"),
    ],
    "shield": [
        dict(duration=4.0,  desc="Invincible for 4s"),
        dict(duration=6.0,  desc="Invincible for 6s"),
        dict(duration=8.0,  desc="Invincible for 8s"),
    ],
    "magnet": [
        dict(duration=6.0,  range=200,  desc="Attract coins (200px) 6s"),
        dict(duration=8.0,  range=275,  desc="Attract coins (275px) 8s"),
        dict(duration=10.0, range=350,  desc="Attract coins (350px) 10s"),
    ],
    "double_coins": [
        dict(duration=8.0,  mult=2, desc="2x coins for 8s"),
        dict(duration=10.0, mult=2, desc="2x coins for 10s"),
        dict(duration=12.0, mult=3, desc="3x coins for 12s"),
    ],
}
UPGRADE_COSTS = [0, 500, 1500]   # price to reach each level (level 0 is free)


def pick_random(rng):
    """Choose a random powerup type using spawn weights."""
    total = sum(p["weight"] for p in POWERUPS)
    r = rng.uniform(0, total)
    for p in POWERUPS:
        r -= p["weight"]
        if r <= 0:
            return p["id"]
    return POWERUPS[-1]["id"]


# ---- Drawing the pickup on the road ----
_glow_cache = {}
_icon_cache = {}


def _make_glow(color, radius=24):
    """Soft circular glow behind the powerup icon."""
    key = (color, radius)
    if key not in _glow_cache:
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -1):
            alpha = int(80 * (1 - i / radius) ** 1.5)
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), i)
        _glow_cache[key] = surf
    return _glow_cache[key]


def _draw_lightning(surf, cx, cy, sz, color, bright):
    """Lightning bolt icon for SPEED."""
    s = sz * 0.55
    pts = [(cx - s * 0.25, cy - s), (cx + s * 0.45, cy - s),
           (cx + s * 0.05, cy - s * 0.1), (cx + s * 0.55, cy - s * 0.1),
           (cx - s * 0.15, cy + s), (cx + s * 0.05, cy + s * 0.15),
           (cx - s * 0.35, cy + s * 0.15)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, bright, pts, 2)


def _draw_heart(surf, cx, cy, sz, color, bright):
    """Heart with a small cross for REGEN."""
    s = sz * 0.4
    # Two circles for top of heart
    pygame.draw.circle(surf, color, (int(cx - s * 0.5), int(cy - s * 0.3)), int(s * 0.6))
    pygame.draw.circle(surf, color, (int(cx + s * 0.5), int(cy - s * 0.3)), int(s * 0.6))
    # Triangle for bottom of heart
    pygame.draw.polygon(surf, color, [(cx - s * 1.1, cy - s * 0.1),
                                       (cx + s * 1.1, cy - s * 0.1),
                                       (cx, cy + s * 1.1)])
    # Cross overlay
    cw = max(2, int(s * 0.25))
    ch = max(4, int(s * 0.7))
    pygame.draw.rect(surf, bright, (cx - cw // 2, cy - ch // 2, cw, ch))
    pygame.draw.rect(surf, bright, (cx - ch // 2, cy - cw // 2, ch, cw))


def _draw_shield(surf, cx, cy, sz, color, bright):
    """Shield/badge shape for SHIELD."""
    s = sz * 0.5
    pts = [(cx, cy - s), (cx + s * 0.85, cy - s * 0.55),
           (cx + s * 0.7, cy + s * 0.3), (cx, cy + s),
           (cx - s * 0.7, cy + s * 0.3), (cx - s * 0.85, cy - s * 0.55)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, bright, pts, 2)
    # Inner chevron
    is_ = s * 0.45
    inner = [(cx, cy - is_ * 0.6), (cx + is_ * 0.5, cy),
             (cx, cy + is_ * 0.6), (cx - is_ * 0.5, cy)]
    pygame.draw.polygon(surf, bright, inner, 2)


def _draw_magnet(surf, cx, cy, sz, color, bright):
    """Horseshoe magnet for MAGNET."""
    s = sz * 0.45
    # U-shape using arc + two rects
    rect = pygame.Rect(cx - s, cy - s * 0.3, s * 2, s * 2)
    pygame.draw.arc(surf, color, rect, math.pi, math.pi * 2, max(3, int(s * 0.4)))
    # Two prongs
    pw = max(3, int(s * 0.4))
    ph = int(s * 0.8)
    pygame.draw.rect(surf, color, (cx - s - pw // 2 + 1, cy - s * 0.3 - ph + s, pw, ph))
    pygame.draw.rect(surf, color, (cx + s - pw // 2, cy - s * 0.3 - ph + s, pw, ph))
    # Red tips
    th = max(3, int(s * 0.3))
    pygame.draw.rect(surf, (220, 50, 50), (cx - s - pw // 2 + 1, cy - s * 0.3 - ph + s, pw, th))
    pygame.draw.rect(surf, (220, 50, 50), (cx + s - pw // 2, cy - s * 0.3 - ph + s, pw, th))


def _draw_double_coins(surf, cx, cy, sz, color, bright):
    """Stacked coins with '2x' text for DOUBLE COINS."""
    s = sz * 0.35
    # Two offset circles as coins
    pygame.draw.circle(surf, (200, 160, 40), (int(cx - s * 0.3), int(cy)), int(s * 0.7))
    pygame.draw.circle(surf, color, (int(cx + s * 0.3), int(cy)), int(s * 0.7))
    pygame.draw.circle(surf, bright, (int(cx + s * 0.3), int(cy)), int(s * 0.7), 2)
    # '2x' label
    try:
        font = pygame.font.SysFont("arial", max(8, int(sz * 0.28)), bold=True)
        txt = font.render("2x", True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=(cx, cy)))
    except Exception:
        pass


_ICON_DRAW = {
    "speed_boost":  _draw_lightning,
    "health_regen": _draw_heart,
    "shield":       _draw_shield,
    "magnet":       _draw_magnet,
    "double_coins": _draw_double_coins,
}


def _get_icon(powerup_id, sz):
    """Return a pre-rendered SRCALPHA surface of the powerup icon at the given size."""
    key = (powerup_id, sz)
    if key not in _icon_cache:
        spec = BY_ID[powerup_id]
        color = spec["color"]
        bright = tuple(min(255, c + 80) for c in color)
        pad = 4
        dim = sz + pad * 2
        s = pygame.Surface((dim, dim), pygame.SRCALPHA)
        _ICON_DRAW[powerup_id](s, dim // 2, dim // 2, sz, color, bright)
        _icon_cache[key] = s
    return _icon_cache[key]


def draw_pickup(surf, sx, sy, powerup_id, t):
    """Draw one powerup pickup at screen coords (sx, sy) with bob and glow."""
    spec = BY_ID[powerup_id]
    color = spec["color"]
    bob = math.sin(t * 3.5) * 5
    pulse = 0.85 + 0.15 * math.sin(t * 5)
    sy_b = sy + bob

    # glow behind the icon
    glow = _make_glow(color)
    surf.blit(glow, glow.get_rect(center=(int(sx), int(sy_b))))

    # icon
    sz = int(28 * pulse)
    icon = _get_icon(powerup_id, sz)
    surf.blit(icon, icon.get_rect(center=(int(sx), int(sy_b))))


def draw_icon_large(surf, cx, cy, powerup_id, t, sz=80):
    """Draw a large version of the icon with animated glow (for the shop screen)."""
    spec = BY_ID[powerup_id]
    color = spec["color"]
    # Glow rings
    for r in range(50, 5, -3):
        alpha = int(50 * (1 - r / 50) ** 1.5)
        gs = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*color, alpha), (r, r), r)
        surf.blit(gs, gs.get_rect(center=(cx, cy)))
    # Icon
    pulse = 0.9 + 0.1 * math.sin(t * 3)
    isz = int(sz * pulse)
    icon = _get_icon(powerup_id, isz)
    surf.blit(icon, icon.get_rect(center=(cx, cy)))


# ---- Active powerup tracker ----
class ActivePowerups:
    """Tracks which powerups are currently running, their remaining time and upgrade levels."""

    def __init__(self):
        self.timers = {}   # powerup_id -> seconds remaining
        self.levels = {}   # powerup_id -> upgrade level (0, 1 or 2)

    def set_levels(self, levels_dict):
        """Load upgrade levels from save data."""
        self.levels = dict(levels_dict)

    def level(self, powerup_id):
        """Current upgrade level (0-indexed)."""
        return self.levels.get(powerup_id, 0)

    def stats(self, powerup_id):
        """Stats dict for a powerup at its current upgrade level."""
        return UPGRADES[powerup_id][self.level(powerup_id)]

    def activate(self, powerup_id):
        """Start (or restart) a powerup using its upgraded duration."""
        self.timers[powerup_id] = self.stats(powerup_id)["duration"]

    def update(self, dt):
        """Tick all timers down; remove expired ones."""
        expired = []
        for pid in self.timers:
            self.timers[pid] -= dt
            if self.timers[pid] <= 0:
                expired.append(pid)
        for pid in expired:
            del self.timers[pid]

    def active(self, powerup_id):
        """True if the powerup is currently running."""
        return powerup_id in self.timers

    def fraction(self, powerup_id):
        """0..1 fraction of time remaining (for the HUD timer bar)."""
        if powerup_id not in self.timers:
            return 0.0
        return max(0.0, self.timers[powerup_id] / self.stats(powerup_id)["duration"])

    def clear(self):
        """Remove all active powerups (used on reset/restart)."""
        self.timers.clear()

    @property
    def active_list(self):
        """List of (powerup_spec, fraction) for every running powerup, sorted by time left."""
        return sorted(
            [(BY_ID[pid], self.fraction(pid)) for pid in self.timers],
            key=lambda x: -x[1]
        )
