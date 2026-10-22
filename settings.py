# settings.py - all constants live here so the whole team tunes the same values

WIDTH, HEIGHT = 1000, 600
FPS = 60
TITLE = "Karachi Kinetic Rickshaw"

# Fixed physics step (seconds). Physics runs at 120 Hz no matter the frame rate.
PHYSICS_DT = 1 / 120

# The screen is in pixels, but the physics and the HUD use metres.
PIXELS_PER_METER = 25
START_X = 100.0       # world x (pixels) where the run starts

# ---- Colours: Pakistani truck-art palette ----
PK_GREEN = (10, 92, 48)
PK_GREEN_DARK = (4, 45, 24)
MARIGOLD = (255, 176, 0)
RED = (206, 32, 41)
WHITE = (255, 255, 255)
LIME = (150, 225, 90)
SHADOW = (10, 22, 14)
ROAD = (90, 80, 70)
ROAD_TOP = (140, 120, 90)
RICKSHAW = (30, 140, 60)

# ---- Driving physics (SI units: kg, N, m/s) ----
MASS = 300.0          # kg
DRIVE_FORCE = 1800.0  # N
BRAKE_FORCE = 2500.0  # N
DRAG = 30.0           # N per (m/s) of speed - simple air/rolling resistance
MAX_SPEED = 400.0     # px/s  (= 16 m/s = about 58 km/h)
MAX_REVERSE = 100.0   # px/s

# ---- Jump / vertical physics (pixels and seconds, a gameplay-tuned value) ----
GRAVITY = 1500.0      # downward acceleration, px/s^2
JUMP_SPEED = 600.0    # initial upward speed when jumping, px/s

# ---- Fuel (CNG) ----
FUEL_MAX = 100.0
FUEL_DRAIN = 3.0           # fuel units used per second of driving
OUT_OF_FUEL_GRACE = 5.0    # seconds you may coast on empty before the run ends

# ---- Images (put your PNGs in the assets folder) ----
RICKSHAW_IMAGE = "assets/rickshaw.png"   # vehicle facing right
RICKSHAW_WIDTH = 120   # drawn width in pixels; height keeps the image's proportions
SPRITE_Y_OFFSET = 0    # increase if the wheels float above the road, decrease if they sink

BACKGROUND_IMAGE = "assets/background.png"
BACKGROUND_MIRROR = True   # mirror every other tile so the join is never visible
BG_PARALLAX = 0.3          # background scrolls at 30% of road speed (depth effect)
MENU_SCROLL_SPEED = 60     # px/s the menu background drifts