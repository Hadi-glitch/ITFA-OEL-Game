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

# ---- Shared driving physics (each vehicle's own mass/force/speed lives in vehicles.py) ----
DRAG = 30.0           # N per (m/s) of speed - simple air/rolling resistance
MAX_REVERSE = 140.0   # px/s

# ---- Jump / vertical physics (pixels and seconds, a gameplay-tuned value) ----
GRAVITY = 1500.0      # downward acceleration, px/s^2
JUMP_SPEED = 600.0    # initial upward speed when jumping, px/s

# ---- Fuel (CNG) ----
FUEL_DRAIN = 3.0           # fuel units used per second of driving
OUT_OF_FUEL_GRACE = 5.0    # seconds you may coast on empty before the run ends

# ---- Economy & saving ----
COIN_VALUE = 5             # rupees per coin collected
START_WALLET = 0           # set to e.g. 10000 while testing to unlock every vehicle
SAVE_FILE = "save.json"    # stored next to main.py

# ---- Background / menu look ----
BG_PARALLAX = 0.3          # skyline scrolls at 30% of road speed (depth effect)
MENU_SCROLL_SPEED = 60     # px/s the menu background drifts

# ---- Animation & feel - tune these by testing ----
SUSP_MAX = 9.0          # max body travel in pixels
PITCH_GAIN = 0.015      # radians of body tilt per m/s^2 (nose lifts when accelerating)
CAMERA_SMOOTH = 6.0     # how quickly the camera catches up (per second)
CAMERA_LOOKAHEAD = 0.12 # camera looks ahead by this fraction of speed
SHAKE_DECAY = 9.0       # how fast screen shake dies out

# ---- Artwork loading ----
ASSET_DEBUG = True      # print a line for every PNG that loads or is missing (set False when art is final)

# ---- Sound ----
SOUND_ON = True        # master switch for effects and music
SFX_VOLUME = 0.7       # 0..1
MUSIC_VOLUME = 0.4     # 0..1 (quieter than effects so they stay clear)

# ---- Powerups ----
POWERUP_SPAWN_CHANCE = 0.06    # chance per terrain cell to contain a powerup
SPEED_BOOST_MULT = 1.4         # max speed multiplier during speed boost
HEALTH_REGEN_TOTAL = 30.0      # total HP restored over the regen duration
MAGNET_RANGE = 200             # pixels: auto-collect coins within this radius