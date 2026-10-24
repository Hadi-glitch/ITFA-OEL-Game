# ui.py - Pakistani truck-art styled HUD, menus and drawing helpers.
# Everything is drawn with Pygame shapes, so no extra art files are needed.
import math
import pygame
import settings as S


class Fonts:
    """All fonts in one place. SysFont tries each name in turn and falls back
    to Pygame's default font if none is installed."""

    def __init__(self):
        heavy = "impact,arialblack,arial"
        self.title = pygame.font.SysFont(heavy, 60)
        self.big = pygame.font.SysFont(heavy, 40)
        self.mid = pygame.font.SysFont(heavy, 28)
        self.small = pygame.font.SysFont("arial", 19, bold=True)
        self.tiny = pygame.font.SysFont("arial", 14, bold=True)


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
def _render(font, text, color, max_width):
    img = font.render(text, True, color)
    if max_width and img.get_width() > max_width:       # shrink long text to fit
        k = max_width / img.get_width()
        img = pygame.transform.smoothscale(
            img, (int(max_width), max(1, int(img.get_height() * k))))
    return img


def draw_text(surf, text, font, color, pos, anchor="center", shadow=True, max_width=None):
    """Draw text positioned by any Rect anchor ('center', 'midleft', 'midright'...)."""
    img = _render(font, text, color, max_width)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        surf.blit(_render(font, text, S.SHADOW, max_width), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def diamond(surf, center, size, color):
    x, y = center
    pygame.draw.polygon(surf, color, [(x, y - size), (x + size, y), (x, y + size), (x - size, y)])


def draw_plaque(surf, rect, fill=S.PK_GREEN, border=S.MARIGOLD, accent=S.RED):
    """The basic truck-art panel: marigold frame, thin white inner line,
    red/marigold diamonds on the edges and dots on the corners."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, S.SHADOW, rect.move(4, 5), border_radius=14)
    pygame.draw.rect(surf, fill, rect, border_radius=14)
    pygame.draw.rect(surf, border, rect, 4, border_radius=14)
    pygame.draw.rect(surf, S.WHITE, rect.inflate(-18, -18), 1, border_radius=9)
    for y in (rect.top, rect.bottom - 1):
        diamond(surf, (rect.centerx, y), 8, accent)
        diamond(surf, (rect.centerx - 22, y), 5, border)
        diamond(surf, (rect.centerx + 22, y), 5, border)
    inner = rect.inflate(-14, -14)
    for corner in (inner.topleft, inner.topright, inner.bottomleft, inner.bottomright):
        pygame.draw.circle(surf, accent, corner, 5)
        pygame.draw.circle(surf, border, corner, 2)


def draw_panel(surf, fonts, rect, heading):
    draw_plaque(surf, rect)
    draw_text(surf, heading, fonts.big, S.MARIGOLD, (rect.centerx, rect.top + 45))


def make_crescent_star(size, color=S.WHITE):
    """Crescent and star icon, built once as a transparent surface.
    A circle is drawn, then a second, transparent circle is punched out of it."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    r = size * 0.42
    pygame.draw.circle(surf, color, (c, c), r)
    pygame.draw.circle(surf, (0, 0, 0, 0), (c + r * 0.3, c), r * 0.8)   # carve the crescent
    sx, sy, sr = c + r * 0.38, c - r * 0.28, r * 0.38
    points = []
    for i in range(10):                                                   # 5-point star
        angle = -math.pi / 2 + i * math.pi / 5
        radius = sr if i % 2 == 0 else sr * 0.4
        points.append((sx + radius * math.cos(angle), sy + radius * math.sin(angle)))
    pygame.draw.polygon(surf, color, points)
    return surf


def draw_title_banner(surf, fonts, icon):
    rect = pygame.Rect(0, 0, 700, 175)
    rect.midtop = (S.WIDTH // 2, 24)
    draw_plaque(surf, rect)
    surf.blit(icon, icon.get_rect(midleft=(rect.left + 28, rect.centery)))
    surf.blit(pygame.transform.flip(icon, True, False),
              icon.get_rect(midright=(rect.right - 28, rect.centery)))
    draw_text(surf, "KARACHI KINETIC", fonts.big, S.WHITE, (rect.centerx, rect.top + 48), max_width=380)
    draw_text(surf, "RICKSHAW", fonts.title, S.MARIGOLD, (rect.centerx, rect.top + 100), max_width=380)
    draw_text(surf, "Meter Down. Physics Up.", fonts.small, S.WHITE,
              (rect.centerx, rect.top + 145), max_width=380)


# --------------------------------------------------------------------------
# Menus
# --------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, action):
        self.rect, self.label, self.action = rect, label, action


class Menu:
    """A vertical list of buttons usable with keyboard (Up/Down/Enter) and mouse.
    handle_event() returns the chosen button's action string, or None."""

    def __init__(self, items, center_x, top, width=300, height=54, gap=14, horizontal=False):
        self.buttons = []
        self.horizontal = horizontal
        total = len(items) * width + (len(items) - 1) * gap
        for i, (label, action) in enumerate(items):
            rect = pygame.Rect(0, 0, width, height)
            if horizontal:                      # buttons side by side, centred on center_x
                rect.topleft = (center_x - total // 2 + i * (width + gap), top)
            else:
                rect.midtop = (center_x, top + i * (height + gap))
            self.buttons.append(Button(rect, label, action))
        self.selected = 0

    def set_labels(self, labels):
        for button, label in zip(self.buttons, labels):
            button.label = label

    def handle_event(self, event):
        n = len(self.buttons)
        if event.type == pygame.MOUSEMOTION:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, b in enumerate(self.buttons):
                if b.rect.collidepoint(event.pos):
                    self.selected = i
                    return b.action
        elif event.type == pygame.KEYDOWN:
            prev_keys = (pygame.K_LEFT, pygame.K_a) if self.horizontal else (pygame.K_UP, pygame.K_w)
            next_keys = (pygame.K_RIGHT, pygame.K_d) if self.horizontal else (pygame.K_DOWN, pygame.K_s)
            if event.key in prev_keys:
                self.selected = (self.selected - 1) % n
            elif event.key in next_keys:
                self.selected = (self.selected + 1) % n
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.buttons[self.selected].action
        return None

    def draw(self, surf, fonts):
        for i, b in enumerate(self.buttons):
            hot = i == self.selected
            r = b.rect
            pygame.draw.rect(surf, S.SHADOW, r.move(3, 4), border_radius=12)
            pygame.draw.rect(surf, S.MARIGOLD if hot else S.PK_GREEN, r, border_radius=12)
            pygame.draw.rect(surf, S.WHITE if hot else S.MARIGOLD, r, 3, border_radius=12)
            draw_text(surf, b.label, fonts.mid, S.PK_GREEN_DARK if hot else S.WHITE,
                      r.center, shadow=not hot, max_width=r.width - 70)
            if hot:
                diamond(surf, (r.left + 22, r.centery), 7, S.RED)
                diamond(surf, (r.right - 22, r.centery), 7, S.RED)


# --------------------------------------------------------------------------
# In-game HUD
# --------------------------------------------------------------------------
def draw_speedometer(surf, fonts, kmh, max_kmh=70, r=100):
    """Half-dial rising from the bottom edge of the screen."""
    cx, cy = S.WIDTH // 2, S.HEIGHT - 10
    pygame.draw.circle(surf, S.SHADOW, (cx + 3, cy + 4), r)
    pygame.draw.circle(surf, S.PK_GREEN, (cx, cy), r)
    pygame.draw.circle(surf, S.MARIGOLD, (cx, cy), r, 7)
    pygame.draw.circle(surf, S.WHITE, (cx, cy), r - 12, 1)

    steps = int(max_kmh // 5)
    for i in range(steps + 1):
        a = math.pi * (1 - i / steps)             # pi = far left, 0 = far right
        major = i % 2 == 0
        r1, r2 = r - (30 if major else 24), r - 16
        p1 = (cx + r1 * math.cos(a), cy - r1 * math.sin(a))
        p2 = (cx + r2 * math.cos(a), cy - r2 * math.sin(a))
        pygame.draw.line(surf, S.WHITE if major else S.MARIGOLD, p1, p2, 3 if major else 2)
        if major:
            rl = r - 44
            draw_text(surf, str(i * 5), fonts.tiny, S.WHITE,
                      (cx + rl * math.cos(a), cy - rl * math.sin(a)), shadow=False)

    # digital readout in the middle
    box = pygame.Rect(cx - 35, cy - 38, 70, 28)
    pygame.draw.rect(surf, S.SHADOW, box, border_radius=6)
    pygame.draw.rect(surf, S.MARIGOLD, box, 1, border_radius=6)
    draw_text(surf, f"{kmh:.0f}", fonts.mid, S.WHITE, box.center, shadow=False, max_width=60)
    draw_text(surf, "km/h", fonts.tiny, S.MARIGOLD, (cx, cy - 5), shadow=False)

    # needle: a thin triangle pointing along angle a
    a = math.pi * (1 - min(kmh / max_kmh, 1.0))
    dx, dy = math.cos(a), -math.sin(a)
    px, py = math.sin(a), math.cos(a)             # perpendicular
    base = (cx + dx * r * 0.5, cy + dy * r * 0.5)
    tip = (cx + dx * r * 0.88, cy + dy * r * 0.88)
    pts = [(base[0] + px * 4, base[1] + py * 4), tip, (base[0] - px * 4, base[1] - py * 4)]
    pygame.draw.polygon(surf, S.RED, pts)
    pygame.draw.polygon(surf, S.WHITE, pts, 1)


def draw_pedal(surf, fonts, rect, label, hint, pressed):
    r = pygame.Rect(rect)
    if pressed:
        r = r.move(0, 4)                          # pedal visibly sinks when pressed
    pygame.draw.rect(surf, S.SHADOW, r.move(3, 4), border_radius=10)
    pygame.draw.rect(surf, S.MARIGOLD if pressed else S.PK_GREEN, r, border_radius=10)
    pygame.draw.rect(surf, S.WHITE if pressed else S.MARIGOLD, r, 3, border_radius=10)
    for i in range(4):                            # grip ribs
        y = r.top + 14 + i * 9
        pygame.draw.line(surf, S.PK_GREEN_DARK if pressed else S.MARIGOLD,
                         (r.left + 14, y), (r.right - 14, y), 3)
    dark = S.PK_GREEN_DARK if pressed else S.WHITE
    draw_text(surf, label, fonts.small, dark, (r.centerx, r.bottom - 30), shadow=not pressed)
    draw_text(surf, hint, fonts.tiny, dark if pressed else S.MARIGOLD,
              (r.centerx, r.bottom - 12), shadow=False)


class HUD:
    def __init__(self, fonts):
        self.f = fonts
        self.icon = make_crescent_star(30)

    def draw(self, surf, r, distance_m, t):
        """Draw the whole in-game HUD: distance, coins/health, fuel, speedometer and pedals."""
        self.draw_distance(surf, distance_m)
        self.draw_status(surf, r)
        self.draw_fuel(surf, r.fuel / r.fuel_max, t)
        kmh = abs(r.speed) / S.PIXELS_PER_METER * 3.6
        draw_speedometer(surf, self.f, kmh)
        draw_pedal(surf, self.f, (20, S.HEIGHT - 112, 84, 92), "BRAKE", "A / Left", r.braking)
        draw_pedal(surf, self.f, (S.WIDTH - 104, S.HEIGHT - 112, 84, 92), "GAS", "D / Right", r.throttle)

    def draw_distance(self, surf, metres):
        rect = pygame.Rect(14, 12, 230, 72)
        draw_plaque(surf, rect)
        draw_text(surf, "DISTANCE", self.f.tiny, S.MARIGOLD, (rect.left + 22, rect.top + 18),
                  "midleft", shadow=False)
        draw_text(surf, f"{int(metres)} m", self.f.big, S.WHITE, (rect.left + 22, rect.top + 46),
                  "midleft", max_width=130)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.right - 20, rect.centery)))

    def draw_status(self, surf, r):
        """Coins collected this run and the vehicle's health bar."""
        rect = pygame.Rect(14, 102, 230, 84)
        draw_plaque(surf, rect)
        pygame.draw.circle(surf, S.MARIGOLD, (rect.left + 32, rect.top + 28), 11)
        pygame.draw.circle(surf, (150, 95, 0), (rect.left + 32, rect.top + 28), 11, 2)
        draw_text(surf, f"x {r.coins}", self.f.mid, S.WHITE, (rect.left + 54, rect.top + 28), "midleft")
        draw_text(surf, f"Rs {r.coins * S.COIN_VALUE}", self.f.tiny, S.MARIGOLD, (rect.right - 22, rect.top + 28), "midright", shadow=False)
        bar = pygame.Rect(rect.left + 22, rect.top + 52, rect.width - 44, 16)
        frac = max(0.0, min(1.0, r.health / r.spec["armor"]))
        pygame.draw.rect(surf, S.PK_GREEN_DARK, bar, border_radius=4)
        colour = S.LIME if frac > 0.5 else (S.MARIGOLD if frac > 0.25 else S.RED)
        pygame.draw.rect(surf, colour, (bar.left, bar.top, int(bar.width * frac), bar.height), border_radius=4)
        pygame.draw.rect(surf, S.WHITE, bar, 1, border_radius=4)
        draw_text(surf, "HEALTH", self.f.tiny, S.WHITE, bar.center, shadow=True)

    def draw_fuel(self, surf, frac, t):
        rect = pygame.Rect(S.WIDTH - 14 - 250, 12, 250, 62)
        draw_plaque(surf, rect)
        draw_text(surf, "CNG", self.f.mid, S.MARIGOLD, (rect.left + 24, rect.centery), "midleft")
        bar = pygame.Rect(rect.left + 92, rect.centery - 13, rect.width - 92 - 24, 26)
        low = frac <= 0.25
        color = S.RED if low else (S.MARIGOLD if frac <= 0.5 else S.LIME)
        if low and int(t * 4) % 2 == 0:
            color = (255, 130, 130)               # blink when nearly empty
        cells, gap = 10, 3
        cw = (bar.width - gap * (cells - 1)) / cells
        lit = math.ceil(frac * cells - 1e-9)
        for i in range(cells):
            cell = pygame.Rect(round(bar.left + i * (cw + gap)), bar.top, round(cw), bar.height)
            pygame.draw.rect(surf, color if i < lit else S.PK_GREEN_DARK, cell, border_radius=3)
        draw_text(surf, "ESC = pause", self.f.tiny, S.WHITE, (S.WIDTH - 18, rect.bottom + 14),
                  "midright")
        if low and int(t * 2) % 2 == 0:
            draw_text(surf, "LOW CNG!", self.f.mid, S.RED, (S.WIDTH // 2, 50))

def wrap_text(font, text, width):
    """Split `text` into lines that each fit inside `width` pixels."""
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if font.size(trial)[0] <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines
