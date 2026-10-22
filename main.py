# main.py - game loop and game states
import math
import os
import random
import pygame
import settings as S
import ui

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAY_STATES = ("playing", "paused", "gameover")

HELP_LINES = [
    ("D / Right", "Accelerate"),
    ("A / Left", "Brake and reverse"),
    ("Space / W / Up", "Jump"),
    ("R", "Restart the run"),
    ("Esc", "Pause"),
]


def road_height(x):
    """Temporary terrain: y position of the road at world x.
    Later this moves to terrain.py as terrain.get_height(x)."""
    return S.HEIGHT - 150 + 40 * math.sin(x / 150) + 25 * math.sin(x / 55)


# --------------------------------------------------------------------------
# Background
# --------------------------------------------------------------------------
def make_fallback_background():
    """Simple dusty skyline, used when assets/background.png is missing."""
    w = S.WIDTH * 2
    surf = pygame.Surface((w, S.HEIGHT))
    top, bottom = (255, 190, 120), (255, 236, 190)
    for y in range(S.HEIGHT):
        t = y / S.HEIGHT
        colour = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surf, colour, (0, y), (w, y))
    pygame.draw.circle(surf, (255, 245, 210), (w // 4, 130), 55)         # hazy sun
    rng = random.Random(7)
    x = 0
    while x < w:
        bw, bh = rng.randint(50, 110), rng.randint(80, 230)
        shade = rng.randint(150, 185)
        top_y = S.HEIGHT - 150 - bh
        pygame.draw.rect(surf, (shade, shade - 25, shade - 45), (x, top_y, bw, bh + 150))
        if rng.random() < 0.25:                                          # dome
            pygame.draw.circle(surf, (shade - 20, shade - 45, shade - 65), (x + bw // 2, top_y), bw // 3)
        x += bw + rng.randint(0, 12)
    return surf


def load_background():
    """Load assets/background.png, scale it to the window height and (optionally)
    mirror it so it can repeat forever without a visible seam."""
    path = os.path.join(BASE_DIR, S.BACKGROUND_IMAGE)
    try:
        img = pygame.image.load(path)
        has_alpha = bool(img.get_flags() & pygame.SRCALPHA)
        img = img.convert_alpha() if has_alpha else img.convert()
        scale = S.HEIGHT / img.get_height()
        img = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * scale)), S.HEIGHT))
    except (pygame.error, FileNotFoundError):
        print(f"Could not load {path} - using the built-in skyline instead.")
        img = make_fallback_background()
    if S.BACKGROUND_MIRROR:
        w = img.get_width()
        wide = pygame.Surface((w * 2, S.HEIGHT), pygame.SRCALPHA)
        wide.blit(img, (0, 0))
        wide.blit(pygame.transform.flip(img, True, False), (w, 0))
        img = wide.convert_alpha()
    return img


# --------------------------------------------------------------------------
# Vehicle
# --------------------------------------------------------------------------
class Rickshaw:
    """Vehicle with driving physics, a jump and a fuel tank.
    Later this moves to vehicle.py."""

    def __init__(self):
        self.image = self.load_image()
        self.reset()

    def load_image(self):
        """Load and scale the PNG. Falls back to a green box if it's missing."""
        path = os.path.join(BASE_DIR, S.RICKSHAW_IMAGE)
        try:
            img = pygame.image.load(path).convert_alpha()
        except (pygame.error, FileNotFoundError):
            print(f"Could not load {path} - using a placeholder box instead.")
            box = pygame.Surface((S.RICKSHAW_WIDTH, S.RICKSHAW_WIDTH // 2), pygame.SRCALPHA)
            pygame.draw.rect(box, S.RICKSHAW, box.get_rect(), border_radius=8)
            return box
        scale = S.RICKSHAW_WIDTH / img.get_width()
        size = (S.RICKSHAW_WIDTH, int(img.get_height() * scale))
        return pygame.transform.smoothscale(img, size)

    def reset(self):
        self.x = S.START_X
        self.speed = 0.0                 # horizontal speed, px/s
        self.y = road_height(self.x)     # y of the vehicle's bottom (wheels)
        self.vy = 0.0                    # vertical speed (positive = falling)
        self.on_ground = True
        self.fuel = S.FUEL_MAX
        self.accel = 0.0                 # m/s^2, shown on the HUD
        self.slope_deg = 0.0             # road angle, positive = uphill
        self.throttle = False
        self.braking = False

    @property
    def air_height(self):
        """Height of the wheels above the road, in metres."""
        return max(0.0, (road_height(self.x) - self.y) / S.PIXELS_PER_METER)

    def jump(self):
        """Called once per key press. Only works while on the ground."""
        if self.on_ground:
            self.vy = -S.JUMP_SPEED      # negative y is upward
            self.on_ground = False

    def update(self, dt, keys):
        self.throttle = bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])
        self.braking = bool(keys[pygame.K_LEFT] or keys[pygame.K_a])

        # ---- Horizontal physics in SI units: force -> acceleration -> speed ----
        v = self.speed / S.PIXELS_PER_METER          # m/s
        force = 0.0
        burning = False
        if self.on_ground:                           # wheels need traction
            if self.throttle and self.fuel > 0:
                force += S.DRIVE_FORCE
                burning = True
            if self.braking:
                if v > 0.1:
                    force -= S.BRAKE_FORCE
                elif self.fuel > 0:                  # reverse
                    force -= S.DRIVE_FORCE * 0.5
                    burning = True
        if burning:
            self.fuel = max(0.0, self.fuel - S.FUEL_DRAIN * dt)
        force -= S.DRAG * v
        self.accel = force / S.MASS                  # Newton's 2nd law: a = F / m
        v += self.accel * dt
        self.speed = max(-S.MAX_REVERSE, min(S.MAX_SPEED, v * S.PIXELS_PER_METER))
        self.x += self.speed * dt

        # ---- Road angle under the rickshaw (for the HUD) ----
        dy = road_height(self.x + 4) - road_height(self.x - 4)
        self.slope_deg = math.degrees(math.atan2(-dy, 8))   # screen y points down

        # ---- Vertical: gravity -> vertical speed -> height ----
        ground_y = road_height(self.x)
        if self.on_ground:
            self.y = ground_y            # stick to the road
        else:
            self.vy += S.GRAVITY * dt
            self.y += self.vy * dt
            if self.y >= ground_y:       # touched the road: land
                self.y = ground_y
                self.vy = 0.0
                self.on_ground = True

    def draw(self, screen, camera_x):
        rect = self.image.get_rect(
            midbottom=(self.x - camera_x, self.y + S.SPRITE_Y_OFFSET))
        screen.blit(self.image, rect)


# --------------------------------------------------------------------------
# Game: a small state machine.  self.state is one of:
#   "menu", "help", "options", "playing", "paused", "gameover"
# --------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.fonts = ui.Fonts()
        self.hud = ui.HUD(self.fonts)
        self.title_icon = ui.make_crescent_star(96)
        self.background = load_background()
        self.rickshaw = Rickshaw()       # created after set_mode so convert_alpha works
        self.dim = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 150))

        cx = S.WIDTH // 2
        self.menus = {
            "menu": ui.Menu([("START", "start"), ("HOW TO PLAY", "help"),
                             ("OPTIONS", "options"), ("EXIT", "exit")], cx, 240),
            "help": ui.Menu([("BACK", "menu")], cx, 450),
            "options": ui.Menu([("", "toggle_physics"), ("", "toggle_fps"),
                                ("BACK", "menu")], cx, 190, width=380),
            "paused": ui.Menu([("RESUME", "resume"), ("RESTART", "restart"),
                               ("MAIN MENU", "menu")], cx, 210),
            "gameover": ui.Menu([("RETRY", "restart"), ("MAIN MENU", "menu")], cx, 335),
        }
        self.state = "menu"
        self.running = True
        self.show_physics = True
        self.show_fps = False
        self.camera_x = 0.0
        self.menu_scroll = 0.0
        self.time = 0.0
        self.dry_time = 0.0
        self.best = 0.0
        self.result = ("", 0.0, False)   # (reason, distance, new_record)

    # ---- helpers ----
    def distance(self):
        return max(0.0, (self.rickshaw.x - S.START_X) / S.PIXELS_PER_METER)

    def set_state(self, state):
        self.state = state
        if state in self.menus:
            self.menus[state].selected = 0

    def start_run(self):
        self.rickshaw.reset()
        self.camera_x = self.rickshaw.x - S.WIDTH * 0.35
        self.dry_time = 0.0
        self.state = "playing"

    def end_run(self, reason):
        d = self.distance()
        self.result = (reason, d, d > self.best)
        self.best = max(self.best, d)
        self.set_state("gameover")

    # ---- events ----
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.state == "playing":
                self.handle_play_event(event)
            else:
                self.handle_menu_event(event)

    def handle_play_event(self, event):
        if event.type == pygame.KEYDOWN:       # one-shot key presses
            if event.key == pygame.K_ESCAPE:
                self.set_state("paused")
            elif event.key == pygame.K_r:
                self.start_run()
            elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                self.rickshaw.jump()

    def handle_menu_event(self, event):
        action = self.menus[self.state].handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                action = {"paused": "resume", "help": "menu", "options": "menu"}.get(self.state, action)
            elif event.key == pygame.K_r and self.state in ("paused", "gameover"):
                action = "restart"
        if action:
            self.do_action(action)

    def do_action(self, action):
        if action in ("start", "restart"):
            self.start_run()
        elif action == "resume":
            self.state = "playing"
        elif action in ("menu", "help", "options"):
            self.set_state(action)
        elif action == "toggle_physics":
            self.show_physics = not self.show_physics
        elif action == "toggle_fps":
            self.show_fps = not self.show_fps
        elif action == "exit":
            self.running = False

    # ---- update (fixed physics step, only while playing) ----
    def update(self, dt):
        if self.state != "playing":
            return
        r = self.rickshaw
        r.update(dt, pygame.key.get_pressed())
        # Camera follows the rickshaw horizontally, keeping it left of centre
        self.camera_x = r.x - S.WIDTH * 0.35
        if r.fuel <= 0:
            self.dry_time += dt
            if r.on_ground and (abs(r.speed) < 5 or self.dry_time > S.OUT_OF_FUEL_GRACE):
                self.end_run("OUT OF CNG!")

    # ---- drawing ----
    def draw_background(self, scroll):
        w = self.background.get_width()
        x = -(scroll % w)
        while x < S.WIDTH:
            self.screen.blit(self.background, (x, 0))
            x += w

    def draw_road(self, camera_x):
        # Sample the terrain every 10 px across the screen
        points = [(0, S.HEIGHT)]
        for sx in range(0, S.WIDTH + 10, 10):
            points.append((sx, road_height(sx + camera_x)))
        points.append((S.WIDTH, S.HEIGHT))
        pygame.draw.polygon(self.screen, S.ROAD, points)
        pygame.draw.lines(self.screen, S.ROAD_TOP, False, points[1:-1], 4)

    def draw(self):
        in_game = self.state in PLAY_STATES
        cam = self.camera_x if in_game else self.menu_scroll
        self.draw_background(cam * S.BG_PARALLAX)
        self.draw_road(cam)
        if in_game:
            self.rickshaw.draw(self.screen, self.camera_x)
            self.hud.draw(self.screen, self.rickshaw, self.distance(), self.show_physics, self.time)
        if self.state in ("paused", "gameover"):
            self.screen.blit(self.dim, (0, 0))

        if self.state == "menu":
            self.draw_main_menu()
        elif self.state == "help":
            self.draw_help()
        elif self.state == "options":
            self.draw_options()
        elif self.state == "paused":
            self.draw_pause()
        elif self.state == "gameover":
            self.draw_gameover()

        if self.show_fps:
            ui.draw_text(self.screen, f"{self.clock.get_fps():.0f} FPS", self.fonts.tiny,
                         S.WHITE, (S.WIDTH // 2, 14))
        pygame.display.flip()

    def draw_main_menu(self):
        ui.draw_title_banner(self.screen, self.fonts, self.title_icon)
        self.menus["menu"].draw(self.screen, self.fonts)
        ui.draw_text(self.screen, "ITFA Project  |  Python + Pygame", self.fonts.tiny,
                     S.WHITE, (S.WIDTH // 2, S.HEIGHT - 18))

    def draw_help(self):
        panel = pygame.Rect(0, 0, 640, 470)
        panel.midtop = (S.WIDTH // 2, 55)
        ui.draw_panel(self.screen, self.fonts, panel, "HOW TO PLAY")
        y = panel.top + 105
        for key, what in HELP_LINES:
            ui.draw_text(self.screen, key, self.fonts.small, S.MARIGOLD, (panel.left + 70, y), "midleft")
            ui.draw_text(self.screen, what, self.fonts.small, S.WHITE, (panel.left + 290, y), "midleft")
            y += 34
        ui.draw_text(self.screen, "Drive as far as you can before your CNG runs out.",
                     self.fonts.small, S.WHITE, (panel.centerx, panel.top + 290), max_width=560)
        ui.draw_text(self.screen, "Wheels only grip the road, so you can't drive in mid-air!",
                     self.fonts.small, S.LIME, (panel.centerx, panel.top + 322), max_width=560)
        self.menus["help"].draw(self.screen, self.fonts)

    def draw_options(self):
        panel = pygame.Rect(0, 0, 500, 330)
        panel.midtop = (S.WIDTH // 2, 100)
        ui.draw_panel(self.screen, self.fonts, panel, "OPTIONS")
        on = lambda flag: "ON" if flag else "OFF"
        self.menus["options"].set_labels([f"PHYSICS INFO: {on(self.show_physics)}",
                                          f"SHOW FPS: {on(self.show_fps)}", "BACK"])
        self.menus["options"].draw(self.screen, self.fonts)

    def draw_pause(self):
        panel = pygame.Rect(0, 0, 400, 340)
        panel.midtop = (S.WIDTH // 2, 115)
        ui.draw_panel(self.screen, self.fonts, panel, "PAUSED")
        self.menus["paused"].draw(self.screen, self.fonts)

    def draw_gameover(self):
        reason, dist, record = self.result
        panel = pygame.Rect(0, 0, 460, 380)
        panel.midtop = (S.WIDTH // 2, 95)
        ui.draw_panel(self.screen, self.fonts, panel, reason)
        cx = panel.centerx
        ui.draw_text(self.screen, "DISTANCE TRAVELLED", self.fonts.tiny, S.MARIGOLD, (cx, 190), shadow=False)
        ui.draw_text(self.screen, f"{int(dist)} m", self.fonts.title, S.WHITE, (cx, 232))
        ui.draw_text(self.screen, f"Best: {int(self.best)} m", self.fonts.small, S.WHITE, (cx, 280))
        if record:
            ui.draw_text(self.screen, "NEW RECORD!", self.fonts.mid, S.LIME, (cx, 308))
        self.menus["gameover"].draw(self.screen, self.fonts)

    # ---- main loop ----
    def run(self):
        accumulator = 0.0
        while self.running:
            frame_time = min(self.clock.tick(S.FPS) / 1000, 0.1)
            self.time += frame_time
            self.handle_events()
            if self.state == "playing":
                accumulator += frame_time
                # Fixed-step physics, kept separate from drawing
                while accumulator >= S.PHYSICS_DT and self.state == "playing":
                    self.update(S.PHYSICS_DT)
                    accumulator -= S.PHYSICS_DT
            else:
                accumulator = 0.0
                if self.state not in PLAY_STATES:
                    self.menu_scroll += S.MENU_SCROLL_SPEED * frame_time
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    Game().run()