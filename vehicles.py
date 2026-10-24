# vehicles.py - the four vehicles: stats, prices, artwork geometry and a loader/drawer for their sprites.
import math
import os
import pygame
import settings as S
import sound

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Geometry numbers (rear/front = hub x, hub y, tyre radius) are measured in the saved PNG, see assets/vehicles.
VEHICLES = [
    dict(id="classic", name="CLASSIC RICKSHAW", price=0, display_w=150,
         blurb="Light, cheap and cheerful. Great for learning the roads.",
         size=(740, 444), rear=(119.6, 420.4, 45.0), front=(677.6, 420.4, 45.0), exhaust=(13, 406), head=None,
         mass=300.0, drive=1800.0, brake=2500.0, max_speed=400.0, fuel=100.0, armor=100.0, susp_k=300.0, susp_c=14.0),
    dict(id="deluxe", name="TRUCK-ART DELUXE", price=1500, display_w=175,
         blurb="Hand-painted beauty with a stronger engine and tank.",
         size=(350, 260), rear=(72.4, 219.5, 35.7), front=(313.3, 220.2, 35.7), exhaust=(24, 207), head=(302, 126),
         mass=340.0, drive=2250.0, brake=2800.0, max_speed=430.0, fuel=120.0, armor=120.0, susp_k=260.0, susp_c=13.0),
    dict(id="chingchi", name="CHINGCHI", price=3500, display_w=190,
         blurb="Motorbike power! Fastest and snappiest, but fragile.",
         size=(380, 220), rear=(85.1, 188.4, 30.9), front=(346.9, 185.8, 33.8), exhaust=(182, 192), head=(331, 116),
         mass=280.0, drive=2700.0, brake=2600.0, max_speed=480.0, fuel=90.0, armor=80.0, susp_k=340.0, susp_c=15.0),
    dict(id="loader", name="LOADER (MASHALLAH)", price=6000, display_w=230,
         blurb="Heavy hauler. Slow to start, huge tank, shrugs off crashes.",
         size=(460, 250), rear=(128.6, 217.4, 32.9), front=(426.7, 216.5, 32.9), exhaust=(206, 217), head=(417, 132),
         mass=520.0, drive=3000.0, brake=3600.0, max_speed=380.0, fuel=170.0, armor=230.0, susp_k=420.0, susp_c=20.0),
]
BY_ID = {v["id"]: v for v in VEHICLES}

# Largest value of each stat, used to draw the stat bars in the garage.
STAT_MAX = {"speed": 480.0, "accel": 9.6, "fuel": 170.0, "armor": 230.0}


def stat_fractions(spec):
    """Return 0..1 bar lengths (speed, accel, fuel, armor) for a vehicle spec."""
    return {"speed": spec["max_speed"] / STAT_MAX["speed"],
            "accel": (spec["drive"] / spec["mass"]) / STAT_MAX["accel"],
            "fuel": spec["fuel"] / STAT_MAX["fuel"],
            "armor": spec["armor"] / STAT_MAX["armor"]}


def _load(name, scale):
    """Load one PNG from assets/vehicles and scale it; return a magenta box if it is missing."""
    path = os.path.join(BASE_DIR, "assets", "vehicles", name)
    try:
        img = pygame.image.load(path).convert_alpha()
        size = (max(1, round(img.get_width() * scale)), max(1, round(img.get_height() * scale)))
        return pygame.transform.smoothscale(img, size)
    except (pygame.error, FileNotFoundError):
        print(f"Missing {path} - copy the assets/vehicles folder next to main.py")
        box = pygame.Surface((max(8, int(100 * scale)), max(8, int(100 * scale))), pygame.SRCALPHA)
        box.fill((255, 0, 255, 160))
        return box


class VehicleArt:
    """Scaled body + wheel pictures for one vehicle, plus every measurement the physics needs."""

    def __init__(self, spec, scale_mult=1.0):
        """Load the sprites and convert the hub/radius numbers into on-screen pixels."""
        self.spec = spec
        k = spec["display_w"] / spec["size"][0] * scale_mult
        self.k = k
        pid = spec["id"]
        self.body = _load(f"{pid}_body.png", k)
        self.wheel_r = _load(f"{pid}_wheel_r.png", k)
        self.wheel_f = _load(f"{pid}_wheel_f.png", k)
        rx, ry, rr = (v * k for v in spec["rear"])
        fx, fy, fr = (v * k for v in spec["front"])
        self.rear_img, self.front_img = (rx, ry), (fx, fy)       # hub positions on the body picture
        self.r_rear, self.r_front = rr, fr                       # tyre radii in pixels
        self.pivot = ((rx + fx) / 2, (ry + fy) / 2)              # point the body rotates around
        self.tilt0 = math.atan2(fy - ry, fx - rx)                # tilt of the hub line inside the picture
        self.exhaust = (spec["exhaust"][0] * k, spec["exhaust"][1] * k)
        self.head = None if not spec["head"] else (spec["head"][0] * k, spec["head"][1] * k)
        self.width, self.height = self.body.get_size()

    def draw_preview(self, surf, center, t):
        """Draw the vehicle upright and standing still with slowly turning wheels (used in the garage)."""
        left = center[0] - self.width / 2
        top = center[1] - self.height / 2
        ang = t * 2.0
        for (hx, hy), img in ((self.rear_img, self.wheel_r), (self.front_img, self.wheel_f)):
            rot = pygame.transform.rotate(img, -math.degrees(ang))
            surf.blit(rot, rot.get_rect(center=(left + hx, top + hy)))
        surf.blit(self.body, (left, top))
