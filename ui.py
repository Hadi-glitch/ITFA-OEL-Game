# ui.py - Pakistani truck-art styled HUD, menus and drawing helpers.
# Enhanced with 3D bevel effects, glassmorphism, gradients, and cached depth rendering.
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
# Caches for ultra-fast 60 FPS rendering of complex 3D surfaces
# --------------------------------------------------------------------------
_text_cache = {}
_plaque_cache = {}
_button_cache = {}
_dial_cache = {}
_pedal_cache = {}
_star_cache = {}


def _render(font, text, color, max_width):
    key = (font, text, color, max_width)
    if key not in _text_cache:
        img = font.render(text, True, color)
        if max_width and img.get_width() > max_width:
            k = max_width / img.get_width()
            img = pygame.transform.smoothscale(
                img, (int(max_width), max(1, int(img.get_height() * k))))
        _text_cache[key] = img
    return _text_cache[key]


def draw_text(surf, text, font, color, pos, anchor="center", shadow=True, max_width=None):
    """Draw text positioned by any Rect anchor ('center', 'midleft', 'midright'...)."""
    img = _render(font, text, color, max_width)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        surf.blit(_render(font, text, S.SHADOW, max_width), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def diamond(surf, center, size, color):
    """Draw a 3D faceted diamond gem with highlight and shadow facets."""
    x, y = center
    pts = [(x, y - size), (x + size, y), (x, y + size), (x - size, y)]
    pygame.draw.polygon(surf, color, pts)
    # Top highlight facet
    hi = tuple(min(255, c + 70) for c in color)
    pygame.draw.line(surf, hi, (x, y - size), (x + size, y), 2)
    pygame.draw.line(surf, hi, (x - size, y), (x, y - size), 2)
    # Bottom shadow facet
    lo = tuple(max(0, c - 50) for c in color)
    pygame.draw.line(surf, lo, (x + size, y), (x, y + size), 2)
    pygame.draw.line(surf, lo, (x, y + size), (x - size, y), 2)
    # Center gleam
    pygame.draw.circle(surf, (255, 255, 255, 180) if len(color) == 3 else (255, 255, 255), (x, y), max(1, size // 4))


def draw_glass_rect(surf, rect, base_color, alpha=180, border_color=None, border_radius=12):
    """Draw a semi-transparent 'glass' rectangle with 3D inner glow and bevel highlight."""
    r = pygame.Rect(rect)
    glass = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
    pygame.draw.rect(glass, (*base_color, alpha), (0, 0, r.width, r.height), border_radius=border_radius)
    # 3D Top specular shine
    pygame.draw.rect(glass, (255, 255, 255, 35), (0, 0, r.width, max(3, r.height // 3)), border_radius=border_radius)
    # 3D Bottom vignette
    pygame.draw.rect(glass, (0, 0, 0, 30), (0, r.height * 2 // 3, r.width, r.height // 3), border_radius=border_radius)
    surf.blit(glass, r.topleft)
    if border_color:
        pygame.draw.rect(surf, border_color, r, 2, border_radius=border_radius)


def get_plaque_surface(w, h, fill=S.PK_GREEN, border=S.MARIGOLD, accent=S.RED):
    """Pre-render a truck-art plaque with multi-layered 3D drop shadow,
    vertical gradient, metallic gold double-bevel, and corner jewels."""
    key = (w, h, fill, border, accent)
    if key in _plaque_cache:
        return _plaque_cache[key]

    pad = 10
    total_w, total_h = w + pad, h + pad
    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, w, h)

    # Multi-layered 3D drop shadow for floating depth
    for i in range(4):
        sr = rect.move(2 + i, 3 + i)
        sa = max(12, 55 - i * 12)
        pygame.draw.rect(surf, (0, 0, 0, sa), sr, border_radius=14)

    # Main panel with rich vertical gradient
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h)
        rc = int(min(255, fill[0] * (1.15 - t * 0.35)))
        gc = int(min(255, fill[1] * (1.20 - t * 0.40)))
        bc = int(min(255, fill[2] * (1.15 - t * 0.35)))
        pygame.draw.line(panel, (rc, gc, bc, 245), (0, y), (w, y))

    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=14)
    panel.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(panel, (0, 0))

    # 3D Top glossy highlight band
    hi_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(hi_surf, (255, 255, 255, 30), (0, 0, w, max(4, h // 4)), border_radius=14)
    hi_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(hi_surf, (0, 0))

    # 3D Metallic Double-Bevel Border
    border_dark = tuple(max(0, c - 50) for c in border)
    border_light = tuple(min(255, c + 50) for c in border)
    pygame.draw.rect(surf, border_dark, rect.inflate(2, 2), 2, border_radius=15)
    pygame.draw.rect(surf, border, rect, 4, border_radius=14)
    # Light highlight along upper & left outer edges
    pygame.draw.line(surf, border_light, (rect.left + 14, rect.top + 1), (rect.right - 14, rect.top + 1), 2)
    pygame.draw.line(surf, border_light, (rect.left + 1, rect.top + 14), (rect.left + 1, rect.bottom - 14), 2)

    # Inner white line with subtle glow
    pygame.draw.rect(surf, S.WHITE, rect.inflate(-18, -18), 1, border_radius=9)

    # Decorative 3D truck-art jewels
    for y in (rect.top, rect.bottom - 1):
        diamond(surf, (rect.centerx, y), 8, accent)
        diamond(surf, (rect.centerx - 24, y), 5, border)
        diamond(surf, (rect.centerx + 24, y), 5, border)

    inner = rect.inflate(-14, -14)
    for corner in (inner.topleft, inner.topright, inner.bottomleft, inner.bottomright):
        pygame.draw.circle(surf, (0, 0, 0, 90), (corner[0] + 1, corner[1] + 1), 6)
        pygame.draw.circle(surf, accent, corner, 5)
        pygame.draw.circle(surf, border_light, corner, 2)

    _plaque_cache[key] = surf
    return surf


def draw_plaque(surf, rect, fill=S.PK_GREEN, border=S.MARIGOLD, accent=S.RED):
    """Blit pre-rendered 3D plaque at rect position."""
    rect = pygame.Rect(rect)
    p_surf = get_plaque_surface(rect.width, rect.height, fill, border, accent)
    surf.blit(p_surf, rect.topleft)


def draw_panel(surf, fonts, rect, heading):
    """Draw a 3D window panel with glowing heading banner."""
    draw_plaque(surf, rect)
    glow_color = tuple(min(255, c + 50) for c in S.MARIGOLD)
    draw_text(surf, heading, fonts.big, glow_color, (rect.centerx, rect.top + 45))
    draw_text(surf, heading, fonts.big, S.MARIGOLD, (rect.centerx, rect.top + 44))


def make_crescent_star(size, color=S.WHITE):
    """Crescent and star emblem with 3D glow."""
    key = (size, color)
    if key in _star_cache:
        return _star_cache[key]
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    r = size * 0.42
    # Soft glowing halo
    for i in range(5):
        alpha = max(5, 25 - i * 5)
        pygame.draw.circle(surf, (*color[:3], alpha) if len(color) >= 3 else (*color, alpha),
                           (int(c), int(c)), int(r + 6 - i))
    pygame.draw.circle(surf, color, (c, c), r)
    pygame.draw.circle(surf, (0, 0, 0, 0), (c + r * 0.3, c), r * 0.8)   # carve crescent
    sx, sy, sr = c + r * 0.38, c - r * 0.28, r * 0.38
    points = []
    for i in range(10):                                                   # 5-point star
        angle = -math.pi / 2 + i * math.pi / 5
        radius = sr if i % 2 == 0 else sr * 0.4
        points.append((sx + radius * math.cos(angle), sy + radius * math.sin(angle)))
    pygame.draw.polygon(surf, color, points)
    _star_cache[key] = surf
    return surf


def draw_title_banner(surf, fonts, icon):
    """Ornate 3D game title banner."""
    rect = pygame.Rect(0, 0, 720, 180)
    rect.midtop = (S.WIDTH // 2, 22)
    draw_plaque(surf, rect)
    surf.blit(icon, icon.get_rect(midleft=(rect.left + 30, rect.centery)))
    surf.blit(pygame.transform.flip(icon, True, False),
              icon.get_rect(midright=(rect.right - 30, rect.centery)))
    # Layered metallic title with golden ambient lighting
    draw_text(surf, "KARACHI KINETIC", fonts.big, (255, 235, 190), (rect.centerx, rect.top + 48), max_width=400)
    draw_text(surf, "RICKSHAW", fonts.title, (255, 215, 60), (rect.centerx, rect.top + 101), max_width=400)
    draw_text(surf, "RICKSHAW", fonts.title, S.MARIGOLD, (rect.centerx, rect.top + 100), max_width=400)
    draw_text(surf, "Meter Down. Physics Up.", fonts.small, (240, 245, 240),
              (rect.centerx, rect.top + 148), max_width=380)


# --------------------------------------------------------------------------
# 3D Menus
# --------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label, action):
        self.rect, self.label, self.action = rect, label, action


def get_button_surface(w, h, hot):
    """Pre-render 3D button plate with specular highlights, bevels, and drop shadow."""
    key = (w, h, hot)
    if key in _button_cache:
        return _button_cache[key]

    pad = 8
    surf = pygame.Surface((w + pad, h + pad), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, w, h)

    # 3D drop shadow
    shadow_depth = 4 if hot else 3
    for j in range(shadow_depth):
        pygame.draw.rect(surf, (0, 0, 0, max(15, 50 - j * 12)),
                         rect.move(2 + j, 3 + j), border_radius=12)

    btn = pygame.Surface((w, h), pygame.SRCALPHA)
    if hot:
        # Hovered: Rich glowing marigold-gold metallic gradient
        for y in range(h):
            t = y / max(1, h)
            rc = int(255 * (1.0 - t * 0.12))
            gc = int(210 - 55 * t)
            bc = int(45 * (1.0 - t))
            pygame.draw.line(btn, (rc, gc, bc, 255), (0, y), (w, y))
    else:
        # Normal: Deep Pakistani truck-art jade green gradient
        for y in range(h):
            t = y / max(1, h)
            rc = int(S.PK_GREEN[0] * (1.1 - t * 0.3))
            gc = int(S.PK_GREEN[1] * (1.2 - t * 0.4))
            bc = int(S.PK_GREEN[2] * (1.1 - t * 0.3))
            pygame.draw.line(btn, (rc, gc, bc, 245), (0, y), (w, y))

    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=12)
    btn.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(btn, (0, 0))

    # 3D Glossy specular shine along upper half
    shine = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(shine, (255, 255, 255, 45 if hot else 25), (0, 0, w, max(4, h // 3)), border_radius=12)
    shine.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(shine, (0, 0))

    # 3D Bevel border
    border_col = S.WHITE if hot else S.MARIGOLD
    border_hi = (255, 255, 255) if hot else (255, 220, 100)
    pygame.draw.rect(surf, border_col, rect, 3, border_radius=12)
    pygame.draw.line(surf, border_hi, (rect.left + 12, rect.top + 1), (rect.right - 12, rect.top + 1), 2)

    _button_cache[key] = surf
    return surf


class Menu:
    """A vertical list of 3D buttons usable with keyboard (Up/Down/Enter) and mouse."""

    def __init__(self, items, center_x, top, width=300, height=54, gap=14, horizontal=False):
        self.buttons = []
        self.horizontal = horizontal
        total = len(items) * width + (len(items) - 1) * gap
        for i, (label, action) in enumerate(items):
            rect = pygame.Rect(0, 0, width, height)
            if horizontal:
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
            btn_surf = get_button_surface(r.width, r.height, hot)
            surf.blit(btn_surf, r.topleft)

            draw_text(surf, b.label, fonts.mid, S.PK_GREEN_DARK if hot else S.WHITE,
                      r.center, shadow=not hot, max_width=r.width - 70)
            if hot:
                diamond(surf, (r.left + 22, r.centery), 7, S.RED)
                diamond(surf, (r.right - 22, r.centery), 7, S.RED)


# --------------------------------------------------------------------------
# In-Game 3D Gauge Speedometer
# --------------------------------------------------------------------------
def get_dial_surface(r, max_kmh=70):
    """Pre-render 3D gauge pod face with metallic chrome ring, tick marks and glass glare."""
    key = (r, max_kmh)
    if key in _dial_cache:
        return _dial_cache[key]

    pad = 16
    sz = (r + pad) * 2
    surf = pygame.Surface((sz, sz), pygame.SRCALPHA)
    cx, cy = r + pad, r + pad

    # Multi-layered 3D shadow
    for i in range(5):
        alpha = max(10, 45 - i * 8)
        pygame.draw.circle(surf, (0, 0, 0, alpha), (cx + 2, cy + 3 + i), r + 4 - i)

    # Radial gradient 3D dial face (gauge pod)
    for rad in range(r, 0, -1):
        t = rad / r
        rc = int(S.PK_GREEN_DARK[0] + (S.PK_GREEN[0] - S.PK_GREEN_DARK[0]) * (1 - t * 0.7))
        gc = int(S.PK_GREEN_DARK[1] + (S.PK_GREEN[1] - S.PK_GREEN_DARK[1]) * (1 - t * 0.7))
        bc = int(S.PK_GREEN_DARK[2] + (S.PK_GREEN[2] - S.PK_GREEN_DARK[2]) * (1 - t * 0.7))
        pygame.draw.circle(surf, (rc, gc, bc), (cx, cy), rad)

    # 3D Chrome Bezel Rings
    pygame.draw.circle(surf, (60, 50, 30), (cx, cy), r + 3, 2)
    pygame.draw.circle(surf, (200, 170, 70), (cx, cy), r + 1, 3)
    pygame.draw.circle(surf, S.MARIGOLD, (cx, cy), r, 4)
    pygame.draw.circle(surf, (255, 235, 140), (cx, cy), r - 2, 1)  # Specular shine
    pygame.draw.circle(surf, (200, 200, 200), (cx, cy), r - 12, 1) # Inner dial rim

    # Tick marks and labels
    fonts_tiny = pygame.font.SysFont("arial", 14, bold=True)
    steps = int(max_kmh // 5)
    for i in range(steps + 1):
        a = math.pi * (1 - i / steps)
        major = i % 2 == 0
        r1, r2 = r - (30 if major else 24), r - 16
        p1 = (cx + r1 * math.cos(a), cy - r1 * math.sin(a))
        p2 = (cx + r2 * math.cos(a), cy - r2 * math.sin(a))
        col = (255, 255, 255) if major else (255, 210, 80)
        pygame.draw.line(surf, col, p1, p2, 3 if major else 2)
        if major:
            rl = r - 44
            lbl = fonts_tiny.render(str(i * 5), True, (255, 255, 255))
            surf.blit(lbl, lbl.get_rect(center=(cx + rl * math.cos(a), cy - rl * math.sin(a))))

    # Glass reflection arc on upper half
    glass_arc = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.circle(glass_arc, (255, 255, 255, 22), (cx, cy - r // 3), r * 3 // 4)
    dial_clip = pygame.Surface((sz, sz), pygame.SRCALPHA)
    pygame.draw.circle(dial_clip, (255, 255, 255, 255), (cx, cy), r - 14)
    glass_arc.blit(dial_clip, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(glass_arc, (0, 0))

    _dial_cache[key] = (surf, cx, cy)
    return _dial_cache[key]


def draw_speedometer(surf, fonts, kmh, max_kmh=70, r=100):
    """Draw 3D tachometer pod with animated glowing needle and LED readout."""
    cx, cy = S.WIDTH // 2, S.HEIGHT - 10
    dial_surf, dcx, dcy = get_dial_surface(r, max_kmh)
    surf.blit(dial_surf, (cx - dcx, cy - dcy))

    # Digital LED readout with bevel glass
    box = pygame.Rect(cx - 38, cy - 40, 76, 30)
    draw_glass_rect(surf, box, (0, 0, 0), alpha=175, border_color=S.MARIGOLD, border_radius=6)
    draw_text(surf, f"{kmh:.0f}", fonts.mid, (210, 255, 210), box.center, shadow=False, max_width=60)
    draw_text(surf, "km/h", fonts.tiny, S.MARIGOLD, (cx, cy - 6), shadow=False)

    # 3D Illuminated Needle with dynamic shadow
    a = math.pi * (1 - min(kmh / max_kmh, 1.0))
    dx, dy = math.cos(a), -math.sin(a)
    px, py = math.sin(a), math.cos(a)
    base = (cx + dx * r * 0.45, cy + dy * r * 0.45)
    tip = (cx + dx * r * 0.88, cy + dy * r * 0.88)

    # Needle drop shadow
    shadow_pts = [(base[0] + px * 4 + 2, base[1] + py * 4 + 3), (tip[0] + 2, tip[1] + 3),
                  (base[0] - px * 4 + 2, base[1] - py * 4 + 3)]
    ns = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
    pygame.draw.polygon(ns, (0, 0, 0, 70), shadow_pts)
    surf.blit(ns, (0, 0))

    # Needle body with specular edge
    pts = [(base[0] + px * 4, base[1] + py * 4), tip, (base[0] - px * 4, base[1] - py * 4)]
    pygame.draw.polygon(surf, S.RED, pts)
    pygame.draw.polygon(surf, (255, 120, 120), pts, 1)

    # 3D Chrome Center Hub
    pygame.draw.circle(surf, (50, 50, 50), (cx, cy), 9)
    pygame.draw.circle(surf, (140, 140, 140), (cx, cy), 7)
    pygame.draw.circle(surf, (220, 220, 220), (cx - 1, cy - 1), 3)


# --------------------------------------------------------------------------
# 3D Pedals
# --------------------------------------------------------------------------
def get_pedal_surface(w, h, pressed):
    """Pre-render 3D pedal with rubber ribs, metallic rim, and spring compression."""
    key = (w, h, pressed)
    if key in _pedal_cache:
        return _pedal_cache[key]

    pad = 8
    surf = pygame.Surface((w + pad, h + pad), pygame.SRCALPHA)
    rect = pygame.Rect(0, 0, w, h)

    # Drop shadow
    for i in range(3):
        pygame.draw.rect(surf, (0, 0, 0, max(15, 45 - i * 12)),
                         rect.move(2 + i, 3 + i), border_radius=10)

    pedal = pygame.Surface((w, h), pygame.SRCALPHA)
    if pressed:
        # Pressed down: gold metallic glow
        for y in range(h):
            t = y / max(1, h)
            rc = int(255 * (1.0 - t * 0.15))
            gc = int(200 - 45 * t)
            bc = int(35 * (1.0 - t))
            pygame.draw.line(pedal, (rc, gc, bc, 255), (0, y), (w, y))
    else:
        # Released: deep truck-art green gradient
        for y in range(h):
            t = y / max(1, h)
            rc = int(S.PK_GREEN[0] * (1.1 - t * 0.3))
            gc = int(S.PK_GREEN[1] * (1.2 - t * 0.4))
            bc = int(S.PK_GREEN[2] * (1.1 - t * 0.3))
            pygame.draw.line(pedal, (rc, gc, bc, 245), (0, y), (w, y))

    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=10)
    pedal.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(pedal, (0, 0))

    # 3D Bevel border
    pygame.draw.rect(surf, S.WHITE if pressed else S.MARIGOLD, rect, 3, border_radius=10)

    # 3D Textured rubber grip ribs
    for i in range(4):
        y = rect.top + 14 + i * 9
        rib_shadow = S.PK_GREEN_DARK if pressed else (30, 25, 15)
        rib_highlight = (255, 240, 160) if pressed else (255, 225, 120)
        pygame.draw.line(surf, rib_shadow, (rect.left + 14, y + 1), (rect.right - 14, y + 1), 3)
        pygame.draw.line(surf, rib_highlight, (rect.left + 14, y - 1), (rect.right - 14, y - 1), 1)
        pygame.draw.line(surf, S.PK_GREEN_DARK if pressed else S.MARIGOLD,
                         (rect.left + 14, y), (rect.right - 14, y), 2)

    _pedal_cache[key] = surf
    return surf


def draw_pedal(surf, fonts, rect, label, hint, pressed):
    """Draw 3D interactive pedal that visibly depresses with spring action."""
    r = pygame.Rect(rect)
    if pressed:
        r = r.move(0, 4)
    p_surf = get_pedal_surface(r.width, r.height, pressed)
    surf.blit(p_surf, r.topleft)

    dark = S.PK_GREEN_DARK if pressed else S.WHITE
    draw_text(surf, label, fonts.small, dark, (r.centerx, r.bottom - 30), shadow=not pressed)
    draw_text(surf, hint, fonts.tiny, dark if pressed else S.MARIGOLD,
              (r.centerx, r.bottom - 12), shadow=False)


# --------------------------------------------------------------------------
# Main HUD Manager
# --------------------------------------------------------------------------
class HUD:
    def __init__(self, fonts):
        self.f = fonts
        self.icon = make_crescent_star(30)

    def draw(self, surf, r, distance_m, t):
        """Draw complete 3D HUD."""
        self.draw_distance(surf, distance_m)
        self.draw_status(surf, r)
        self.draw_fuel(surf, r.fuel / r.fuel_max, t)
        kmh = abs(r.speed) / S.PIXELS_PER_METER * 3.6
        draw_speedometer(surf, self.f, kmh)
        draw_pedal(surf, self.f, (20, S.HEIGHT - 112, 84, 92), "BRAKE", "A / Left", r.braking)
        draw_pedal(surf, self.f, (S.WIDTH - 104, S.HEIGHT - 112, 84, 92), "GAS", "D / Right", r.throttle)

    def draw_distance(self, surf, metres):
        """Distance plaque with metallic emblem."""
        rect = pygame.Rect(14, 12, 230, 72)
        draw_plaque(surf, rect)
        draw_text(surf, "DISTANCE", self.f.tiny, S.MARIGOLD, (rect.left + 22, rect.top + 18),
                  "midleft", shadow=False)
        draw_text(surf, f"{int(metres)} m", self.f.big, S.WHITE, (rect.left + 22, rect.top + 46),
                  "midleft", max_width=130)
        surf.blit(self.icon, self.icon.get_rect(midright=(rect.right - 20, rect.centery)))

    def draw_status(self, surf, r):
        """Coins collected and 3D health bar."""
        rect = pygame.Rect(14, 102, 230, 84)
        draw_plaque(surf, rect)
        # 3D Coin with gold shine
        pygame.draw.circle(surf, (150, 95, 0), (rect.left + 33, rect.top + 29), 12)
        pygame.draw.circle(surf, S.MARIGOLD, (rect.left + 32, rect.top + 28), 11)
        pygame.draw.circle(surf, (255, 230, 110), (rect.left + 30, rect.top + 26), 5)
        pygame.draw.circle(surf, (170, 110, 10), (rect.left + 32, rect.top + 28), 11, 2)
        draw_text(surf, f"x {r.coins}", self.f.mid, S.WHITE, (rect.left + 54, rect.top + 28), "midleft")
        draw_text(surf, f"Rs {r.coins * S.COIN_VALUE}", self.f.tiny, S.MARIGOLD, (rect.right - 22, rect.top + 28), "midright", shadow=False)

        # 3D Health Bar with inner depth and specular shine
        bar = pygame.Rect(rect.left + 22, rect.top + 52, rect.width - 44, 16)
        frac = max(0.0, min(1.0, r.health / r.spec["armor"]))
        pygame.draw.rect(surf, (2, 25, 12), bar, border_radius=4)
        pygame.draw.rect(surf, S.PK_GREEN_DARK, bar.inflate(-2, -2), border_radius=3)
        colour = S.LIME if frac > 0.5 else (S.MARIGOLD if frac > 0.25 else S.RED)
        fill_w = int(bar.width * frac)
        if fill_w > 0:
            fill_rect = pygame.Rect(bar.left, bar.top, fill_w, bar.height)
            pygame.draw.rect(surf, colour, fill_rect, border_radius=4)
            hi_col = tuple(min(255, c + 60) for c in colour)
            pygame.draw.rect(surf, hi_col, (fill_rect.left + 2, fill_rect.top + 2, fill_rect.width - 4, 4), border_radius=2)
        pygame.draw.rect(surf, S.WHITE, bar, 1, border_radius=4)
        draw_text(surf, "HEALTH", self.f.tiny, S.WHITE, bar.center, shadow=True)

    def draw_fuel(self, surf, frac, t):
        """3D CNG cylinder gauge with glowing segmented cells."""
        rect = pygame.Rect(S.WIDTH - 14 - 250, 12, 250, 62)
        draw_plaque(surf, rect)
        draw_text(surf, "CNG", self.f.mid, S.MARIGOLD, (rect.left + 24, rect.centery), "midleft")
        bar = pygame.Rect(rect.left + 92, rect.centery - 13, rect.width - 92 - 24, 26)
        low = frac <= 0.25
        color = S.RED if low else (S.MARIGOLD if frac <= 0.5 else S.LIME)
        if low and int(t * 4) % 2 == 0:
            color = (255, 130, 130)

        cells, gap = 10, 3
        cw = (bar.width - gap * (cells - 1)) / cells
        lit = math.ceil(frac * cells - 1e-9)
        for i in range(cells):
            cell = pygame.Rect(round(bar.left + i * (cw + gap)), bar.top, round(cw), bar.height)
            if i < lit:
                pygame.draw.rect(surf, color, cell, border_radius=3)
                hi = tuple(min(255, c + 60) for c in color)
                pygame.draw.rect(surf, hi, (cell.left + 1, cell.top + 1, cell.width - 2, 7), border_radius=2)
            else:
                pygame.draw.rect(surf, S.PK_GREEN_DARK, cell, border_radius=3)
            pygame.draw.rect(surf, (0, 0, 0, 80), cell, 1, border_radius=3)

        draw_text(surf, "ESC = pause", self.f.tiny, S.WHITE, (S.WIDTH - 18, rect.bottom + 14), "midright")
        if low and int(t * 2) % 2 == 0:
            draw_text(surf, "LOW CNG!", self.f.mid, S.RED, (S.WIDTH // 2, 50))

    def draw_active_powerups(self, surf, active_list, t):
        """Active powerup status badges with glass styling and mini progress bars."""
        if not active_list:
            return
        total_w = len(active_list) * 76 + (len(active_list) - 1) * 6
        start_x = S.WIDTH // 2 - total_w // 2
        for idx, (spec, frac) in enumerate(active_list):
            x = start_x + idx * 82
            box = pygame.Rect(x, 12, 74, 44)
            draw_glass_rect(surf, box, S.PK_GREEN_DARK, alpha=210, border_color=spec["color"], border_radius=6)
            draw_text(surf, spec["name"], self.f.tiny, spec["color"],
                      (box.centerx, box.top + 14), shadow=False)
            bar = pygame.Rect(box.left + 5, box.bottom - 10, box.width - 10, 5)
            pygame.draw.rect(surf, (20, 20, 20), bar, border_radius=2)
            fill_w = int(bar.width * frac)
            if fill_w > 0:
                pygame.draw.rect(surf, spec["color"],
                                 (bar.left, bar.top, fill_w, bar.height), border_radius=2)
                hi = tuple(min(255, c + 60) for c in spec["color"])
                pygame.draw.rect(surf, hi, (bar.left, bar.top, fill_w, 2), border_radius=1)


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
