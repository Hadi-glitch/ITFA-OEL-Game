# obstacles.py - rocks, barrels, cars, coins, CNG cans: drawing, collisions, pickups and road marks.
import math
import random
import pygame
import settings as S
import terrain

# Damage dealt by each obstacle (absolute health points; vehicles have 80-230 health).
DAMAGE = {"rock": 28, "cart": 22, "car": 35, "barricade": 16, "barrel": 9, "cone": 3, "garbage": 6}
KNOCK = ("barrel", "cone", "barricade")          # these get knocked flying and the vehicle keeps going
SOFT = ("garbage",)                              # slows you down but is not solid
SOLID = ("rock", "cart", "car")                  # these stop you: jump over them or reverse
SPEED_KEEP = {"cone": 0.85, "barrel": 0.7, "barricade": 0.45, "garbage": 0.6}   # speed left after hitting
CAR_COLOURS = [(235, 235, 235), (150, 160, 170), (190, 40, 45), (50, 90, 160)]


# --------------------------------------------------------------------------
# Sprites (drawn once with shapes, then cached)
# --------------------------------------------------------------------------
def make_sprite(kind, w, h, variant):
    """Draw one obstacle picture of size w x h (bottom edge sits on the road)."""
    rng = random.Random(variant * 977 + w * 31 + h)
    s = pygame.Surface((int(w), int(h)), pygame.SRCALPHA)
    outline = (25, 22, 20)
    if kind == "rock":
        pts = []
        for i in range(10):                                           # lumpy ellipse
            a = math.pi + i * math.pi / 9
            pts.append((w / 2 + math.cos(a) * w / 2 * rng.uniform(0.82, 1.0), h + math.sin(a) * h * rng.uniform(0.82, 1.0)))
        pygame.draw.polygon(s, (122, 116, 108), pts)
        pygame.draw.polygon(s, (168, 160, 148), [p for p in pts[1:6]] + [(w * 0.45, h * 0.5)])   # lit upper-left
        pygame.draw.polygon(s, outline, pts, 3)
        pygame.draw.line(s, (80, 75, 70), (w * 0.55, h * 0.25), (w * 0.62, h * 0.7), 2)           # crack
    elif kind == "barrel":
        pygame.draw.rect(s, (235, 105, 25), (0, 0, w, h), border_radius=5)
        for y in (h * 0.22, h * 0.58):
            pygame.draw.rect(s, (245, 245, 240), (0, y, w, h * 0.14))
        pygame.draw.rect(s, outline, (0, 0, w, h), 3, border_radius=5)
    elif kind == "cone":
        pygame.draw.polygon(s, (240, 110, 30), [(w / 2, 0), (w * 0.88, h * 0.86), (w * 0.12, h * 0.86)])
        pygame.draw.polygon(s, (245, 245, 240), [(w * 0.36, h * 0.34), (w * 0.64, h * 0.34), (w * 0.72, h * 0.54), (w * 0.28, h * 0.54)])
        pygame.draw.rect(s, (40, 40, 40), (0, h * 0.84, w, h * 0.16))
    elif kind == "barricade":
        for x in (w * 0.1, w * 0.78):                                  # legs
            pygame.draw.rect(s, (60, 60, 64), (x, h * 0.3, w * 0.1, h * 0.7))
        for y in (0, h * 0.34):                                        # two striped boards
            pygame.draw.rect(s, (245, 245, 240), (0, y, w, h * 0.26))
            for x in range(-10, int(w), 18):
                pygame.draw.polygon(s, (205, 35, 35), [(x, y + h * 0.26), (x + 9, y + h * 0.26), (x + 19, y), (x + 10, y)])
            pygame.draw.rect(s, outline, (0, y, w, h * 0.26), 2)
    elif kind == "garbage":
        for _ in range(int(w / 7)):                                    # heap of coloured bags
            r = rng.randint(7, 13)
            col = rng.choice([(60, 60, 60), (230, 230, 225), (200, 90, 40), (80, 120, 70), (150, 150, 160)])
            x, y = rng.uniform(r, w - r), h - r - rng.uniform(0, h * 0.45)
            pygame.draw.circle(s, col, (int(x), int(y)), r)
            pygame.draw.circle(s, outline, (int(x), int(y)), r, 1)
    elif kind == "cart":
        pygame.draw.rect(s, (150, 100, 55), (4, h * 0.38, w - 8, h * 0.28))               # bed
        for x in range(10, int(w) - 8, 14):
            pygame.draw.line(s, (100, 65, 35), (x, h * 0.38), (x, h * 0.66), 2)
        for i in range(6):                                                              # fruit on the cart
            pygame.draw.circle(s, rng.choice([(235, 140, 30), (200, 40, 40), (240, 210, 50)]),
                               (int(14 + i * (w - 28) / 5), int(h * 0.34)), 7)
        pygame.draw.line(s, (100, 65, 35), (w - 6, h * 0.5), (w + 0, h * 0.1), 3)       # handle
        cx, cy, r = w * 0.45, h - 11, 11
        pygame.draw.circle(s, (30, 30, 30), (int(cx), int(cy)), r)
        pygame.draw.circle(s, (190, 190, 190), (int(cx), int(cy)), r - 4)
        for a in range(4):
            ang = a * math.pi / 4
            pygame.draw.line(s, (90, 90, 90), (cx - math.cos(ang) * (r - 4), cy - math.sin(ang) * (r - 4)),
                             (cx + math.cos(ang) * (r - 4), cy + math.sin(ang) * (r - 4)), 1)
    elif kind == "car":
        c = CAR_COLOURS[variant % len(CAR_COLOURS)]
        dark = tuple(max(0, v - 60) for v in c)
        pygame.draw.polygon(s, c, [(2, h - 12), (4, h * 0.55), (w * 0.22, h * 0.48), (w * 0.34, h * 0.14),
                                   (w * 0.7, h * 0.14), (w * 0.82, h * 0.48), (w - 3, h * 0.55), (w - 2, h - 12)])
        pygame.draw.polygon(s, (170, 215, 235), [(w * 0.38, h * 0.2), (w * 0.67, h * 0.2), (w * 0.76, h * 0.46), (w * 0.3, h * 0.46)])
        pygame.draw.line(s, dark, (w * 0.53, h * 0.2), (w * 0.53, h * 0.46), 2)
        pygame.draw.rect(s, dark, (0, h - 16, w, 6))
        for cx in (w * 0.22, w * 0.78):
            pygame.draw.circle(s, (25, 25, 25), (int(cx), h - 10), 10)
            pygame.draw.circle(s, (170, 170, 175), (int(cx), h - 10), 5)
        pygame.draw.rect(s, (255, 210, 60), (w - 8, h * 0.58, 6, 6))                  # headlight
        pygame.draw.rect(s, (220, 40, 40), (2, h * 0.58, 5, 6))                       # taillight
    return s


# --------------------------------------------------------------------------
# Manager
# --------------------------------------------------------------------------
class Hazards:
    """Looks after everything on the road that is not terrain: obstacles, pickups, debris and road marks."""

    def __init__(self):
        """Prepare caches and the small pictures for coins and CNG cylinders."""
        self.sprites = {}
        self.state = {}          # id -> "hit" / "taken" (what already happened this run)
        self.debris = []
        font = pygame.font.SysFont("arial", 11, bold=True)
        self.cng = pygame.Surface((22, 32), pygame.SRCALPHA)
        pygame.draw.rect(self.cng, (30, 150, 70), (0, 4, 22, 28), border_radius=8)
        pygame.draw.rect(self.cng, (200, 200, 205), (7, 0, 8, 6))
        pygame.draw.rect(self.cng, (15, 15, 15), (0, 4, 22, 28), 2, border_radius=8)
        txt = font.render("CNG", True, S.WHITE)
        self.cng.blit(txt, txt.get_rect(center=(11, 19)))

    def reset(self):
        """Forget what was hit/collected so the course is fresh for a new run."""
        self.state.clear()
        self.debris.clear()

    def sprite(self, o):
        """Return the cached picture for an obstacle, drawing it the first time."""
        key = (o["kind"], int(o["w"]), int(o["h"]), o["variant"])
        if key not in self.sprites:
            self.sprites[key] = make_sprite(o["kind"], o["w"], o["h"], o["variant"])
        return self.sprites[key]

    # ---------------- physics-side ----------------
    def update(self, r, dt, fx):
        """One physics step: crash into obstacles, pick up coins/CNG and move flying debris."""
        r.hit_cooldown = max(0.0, r.hit_cooldown - dt)
        front_x = r.x + r.front_ext
        for cell in range(math.floor((r.x - r.rear_ext - 60) / terrain.CELL), math.floor((r.x + r.front_ext + 60) / terrain.CELL) + 1):
            content = terrain.cell_content(cell)
            for i, o in enumerate(content["obs"]):
                if self.state.get((cell, i, "o")) == "hit":
                    continue
                ground = terrain.get_height(o["x0"] + o["w"] / 2)
                if o["x0"] <= front_x <= o["x0"] + o["w"] + 6 and r.y > ground - 0.85 * o["h"]:
                    self.crash(r, o, (cell, i, "o"), ground, fx)
            for i, p in enumerate(content["pick"]):
                if self.state.get((cell, i, "p")):
                    continue
                py = terrain.get_height(p["x"]) - p["up"]
                if r.x - r.rear_ext < p["x"] < front_x - 6 and r.y - r.height * 0.8 < py < r.y + 8:
                    self.state[(cell, i, "p")] = True
                    if p["kind"] == "coin":
                        r.coins += 1
                        colour = S.MARIGOLD
                    else:
                        r.fuel = min(r.fuel_max, r.fuel + 35)
                        colour = S.LIME
                    for _ in range(6):
                        fx.emit(p["x"], py, random.uniform(-70, 70), random.uniform(-120, -20), 0.45, 3, 1, colour, 220, 300)
        self.update_debris(dt)

    def crash(self, r, o, key, ground, fx):
        """Apply the effect of hitting obstacle `o`: damage, speed loss, push-back or knock-over, and effects."""
        kind = o["kind"]
        speed_in = abs(r.speed)
        if kind in SOLID:
            if r.hit_cooldown <= 0 and speed_in > 40:                # gentle nudges do no damage
                r.health -= max(3.0, DAMAGE[kind] * min(1.0, speed_in / 250))
                r.hit_cooldown = 0.4
                r.impact = max(r.impact, min(speed_in / 50, 8.0))
                for _ in range(8):
                    fx.emit(o["x0"], ground - o["h"] * 0.5, random.uniform(-160, 20), random.uniform(-150, -20), 0.5, 2, 5, (210, 190, 150), 200, 250)
            r.x = o["x0"] - r.front_ext - 1                          # solid: we cannot pass
            r.speed = -min(speed_in * 0.25, 60.0)                    # small bounce back
            return
        self.state[key] = "hit"
        r.health -= DAMAGE[kind]
        r.speed *= SPEED_KEEP[kind]
        r.impact = max(r.impact, min(speed_in / 60, 6.0))
        r.hit_cooldown = 0.2
        if kind in KNOCK:
            self.debris.append(dict(sprite=self.sprite(o), x=o["x0"] + o["w"] / 2, y=ground - o["h"] / 2,
                                    vx=max(r.speed, 60) * 1.1 + random.uniform(20, 120), vy=-random.uniform(220, 420),
                                    ang=0.0, spin=random.uniform(-9, 9), life=1.3))
        else:                                                          # garbage bursts into scraps
            for _ in range(10):
                fx.emit(o["x0"] + o["w"] / 2, ground - o["h"], random.uniform(-80, 160), random.uniform(-220, -60),
                        0.6, 3, 3, random.choice([(230, 230, 225), (80, 80, 80), (200, 90, 40)]), 230, 700)

    def update_debris(self, dt):
        """Move flying (knocked) obstacles with simple gravity and remove old ones."""
        alive = []
        for d in self.debris:
            d["life"] -= dt
            if d["life"] > 0:
                d["vy"] += S.GRAVITY * dt
                d["x"] += d["vx"] * dt
                d["y"] += d["vy"] * dt
                d["ang"] += d["spin"] * dt
                alive.append(d)
        self.debris = alive

    # ---------------- drawing ----------------
    def draw_ground_marks(self, surf, cam, t):
        """Paint potholes (dark inside, sewage water on some) and striped speed breakers on the road."""
        lyari = terrain.current()["id"] == "lyari"
        for f in terrain.features_in(cam - 80, cam + S.WIDTH + 80):
            x_start, x_end = int(f["c"] - f["hw"]), int(f["c"] + f["hw"])
            if f["kind"] == "pothole":
                level = terrain.get_height(f["c"] - f["hw"] - 2) + f["amount"] * 0.45   # water surface y
                water = lyari or int(f["c"]) % 3 == 0
                for wx in range(x_start, x_end + 1, 3):
                    y = terrain.get_height(wx)
                    sx = wx - cam
                    pygame.draw.line(surf, (30, 26, 22), (sx, y), (sx, y + 6), 3)
                    if water and y > level:
                        pygame.draw.line(surf, (74, 104, 92), (sx, level), (sx, y), 3)
                        if int(wx / 3 + t * 3) % 6 == 0:                        # little shimmer
                            pygame.draw.line(surf, (150, 180, 170), (sx, level), (sx + 2, level), 2)
            else:
                for k, wx in enumerate(range(x_start, x_end, 8)):
                    a = (wx - cam, terrain.get_height(wx) + 1)
                    b = (wx + 8 - cam, terrain.get_height(wx + 8) + 1)
                    pygame.draw.line(surf, (240, 205, 40) if k % 2 == 0 else (30, 30, 30), a, b, 5)

    def draw(self, surf, cam, t):
        """Draw visible obstacles, pickups and flying debris."""
        for cell in range(math.floor(cam / terrain.CELL) - 1, math.floor((cam + S.WIDTH) / terrain.CELL) + 2):
            content = terrain.cell_content(cell)
            for i, o in enumerate(content["obs"]):
                if self.state.get((cell, i, "o")) == "hit":
                    continue
                ground = terrain.get_height(o["x0"] + o["w"] / 2)
                surf.blit(self.sprite(o), (o["x0"] - cam, ground - o["h"] + 3))
            for i, p in enumerate(content["pick"]):
                if self.state.get((cell, i, "p")):
                    continue
                sx, sy = p["x"] - cam, terrain.get_height(p["x"]) - p["up"]
                if p["kind"] == "coin":
                    wdt = max(3, int(abs(math.cos(t * 4 + p["x"] * 0.03)) * 16))   # spinning coin: squash its width
                    pygame.draw.ellipse(surf, S.MARIGOLD, (sx - wdt / 2, sy - 9, wdt, 18))
                    pygame.draw.ellipse(surf, (150, 95, 0), (sx - wdt / 2, sy - 9, wdt, 18), 2)
                    if wdt > 8:
                        pygame.draw.ellipse(surf, (255, 225, 120), (sx - wdt / 4, sy - 5, wdt / 2, 10), 1)
                else:
                    bob = math.sin(t * 3 + p["x"]) * 3
                    surf.blit(self.cng, self.cng.get_rect(center=(sx, sy + bob)))
        for d in self.debris:
            rot = pygame.transform.rotate(d["sprite"], -math.degrees(d["ang"]))
            surf.blit(rot, rot.get_rect(center=(d["x"] - cam, d["y"])))
