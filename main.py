# main.py - game loop, game states, camera, drawing order, garage and map screens.
import math
import random
import pygame
import settings as S
import ui
import terrain
import effects
import maps
import save
import vehicles
from vehicle import Rickshaw
from obstacles import Hazards
import assets; assets.load_image("backgrounds", "university.png")

PLAY_STATES = ("playing", "paused", "gameover")
DIM_STATES = ("paused", "gameover", "garage", "maps")
SKY = (255, 205, 140)          # fills the screen edges while the screen shakes

HELP_LINES = [
    ("D / Right", "Accelerate"),
    ("A / Left", "Brake and reverse"),
    ("Space / W / Up", "Jump"),
    ("R", "Restart the run"),
    ("Esc", "Pause"),
]


def money(n):
    """Format rupees with thousands separators, e.g. 'Rs 3,500'."""
    return f"Rs {int(n):,}"


# --------------------------------------------------------------------------
# Game: a small state machine.  self.state is one of:
#   "menu", "help", "options", "garage", "maps", "playing", "paused", "gameover"
# --------------------------------------------------------------------------
class Game:
    def __init__(self):
        """Create the window, load art and the save file, build menus and set every counter to its start value."""
        pygame.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.fonts = ui.Fonts()
        self.hud = ui.HUD(self.fonts)
        self.title_icon = ui.make_crescent_star(96)
        self.world = pygame.Surface((S.WIDTH, S.HEIGHT))    # the world is drawn here, then shaken onto the screen
        self.save = save.load()
        self.arts = {v["id"]: vehicles.VehicleArt(v) for v in vehicles.VEHICLES}                 # in-game sprites
        self.preview_arts = {v["id"]: vehicles.VehicleArt(v, 1.35) for v in vehicles.VEHICLES}   # bigger, for the garage
        self.map_bg = {m["id"]: maps.build_background(m) for m in maps.MAPS}
        self.map_thumb = {m["id"]: self.make_thumb(m) for m in maps.MAPS}
        self.rickshaw = None                                # created when a run starts
        self.fx = effects.ParticleSystem()
        self.clouds = effects.Clouds()
        self.scenery = effects.Scenery()
        self.hazards = Hazards()
        self.dim = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 150))

        cx = S.WIDTH // 2
        browse = [("<", "prev"), ("", "act"), (">", "next"), ("BACK", "menu")]
        self.menus = {
            "menu": ui.Menu([("START", "start"), ("GARAGE", "garage"), ("HOW TO PLAY", "help"),
                             ("OPTIONS", "options"), ("EXIT", "exit")], cx, 226, height=48, gap=10),
            "help": ui.Menu([("BACK", "menu")], cx, 490),
            "options": ui.Menu([("", "toggle_fps"), ("BACK", "menu")], cx, 220, width=380),
            "paused": ui.Menu([("RESUME", "resume"), ("RESTART", "restart"),
                               ("MAIN MENU", "menu")], cx, 210),
            "gameover": ui.Menu([("RETRY", "restart"), ("MAIN MENU", "menu")], cx, 350),
            "garage": ui.Menu(browse, cx, 487, width=150, height=48, gap=12, horizontal=True),
            "maps": ui.Menu(list(browse), cx, 487, width=150, height=48, gap=12, horizontal=True),
        }
        self.state = "menu"
        self.running = True
        self.show_fps = False
        self.camera_x = 0.0
        self.menu_scroll = 0.0
        self.shake = 0.0
        self.time = 0.0
        self.dry_time = 0.0
        self.g_idx = 0                    # vehicle being browsed in the garage
        self.m_idx = 0                    # map being browsed
        self.message = ("", 0.0)          # (text, seconds left) shown in the garage
        self.result = {}
        self.background = None
        self.apply_map(maps.BY_ID.get(self.save["map"], maps.MAPS[0]))

    # ---- helpers ----
    def make_thumb(self, m):
        """Small preview picture of a map: its skyline with a road in the map's colours."""
        thumb = pygame.transform.smoothscale(self.map_bg[m["id"]].subsurface((0, 0, S.WIDTH, S.HEIGHT)), (430, 258))
        pts = [(0, 258)] + [(x, 205 + 14 * math.sin(x / 40) + 8 * math.sin(x / 17)) for x in range(0, 431, 10)] + [(430, 258)]
        pygame.draw.polygon(thumb, m["road"], pts)
        pygame.draw.lines(thumb, m["road_top"], False, pts[1:-1], 3)
        return thumb

    def apply_map(self, m):
        """Make `m` the active map: terrain, hazards and skyline all follow it."""
        terrain.set_map(m)
        self.background = self.map_bg[m["id"]]

    def persist(self):
        """Write the save file."""
        save.write(self.save)

    def selected_map(self):
        """The map dict chosen for the next run."""
        return maps.BY_ID.get(self.save["map"], maps.MAPS[0])

    def distance(self):
        """Distance driven from the start line, in metres."""
        return max(0.0, (self.rickshaw.x - S.START_X) / S.PIXELS_PER_METER)

    def set_state(self, state):
        """Switch state; browse screens start on the currently selected vehicle/map."""
        self.state = state
        if state in self.menus:
            self.menus[state].selected = 0
        if state == "garage":
            self.g_idx = [v["id"] for v in vehicles.VEHICLES].index(self.save["vehicle"])
            self.menus[state].selected = 1
            self.message = ("", 0.0)
        elif state == "maps":
            self.m_idx = [m["id"] for m in maps.MAPS].index(self.save["map"])
            self.menus[state].selected = 1
        if state in ("menu", "help", "options", "garage"):
            self.apply_map(self.selected_map())

    def start_run(self):
        """Create/reset the vehicle for the selected map and begin playing."""
        m = self.selected_map()
        self.apply_map(m)
        vid = self.save["vehicle"]
        if self.rickshaw is None or self.rickshaw.spec["id"] != vid:
            self.rickshaw = Rickshaw(self.arts[vid])
        self.rickshaw.reset()
        self.hazards.reset()
        self.fx.clear()
        self.shake = 0.0
        self.camera_x = self.rickshaw.x - S.WIDTH * 0.35
        self.dry_time = 0.0
        self.state = "playing"

    def end_run(self, reason):
        """Pay out the coins, store the best distance, save, and show the game-over panel."""
        d = self.distance()
        earned = self.rickshaw.coins * S.COIN_VALUE
        mid = self.selected_map()["id"]
        best = self.save["best"].get(mid, 0.0)
        self.result = dict(reason=reason, dist=d, record=d > best, coins=self.rickshaw.coins, earned=earned)
        self.save["best"][mid] = max(best, d)
        self.save["wallet"] += earned
        self.persist()
        self.set_state("gameover")

    # ---- events ----
    def handle_events(self):
        """Read the OS event queue and route each event to play, browse or menu handling."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.state == "playing":
                self.handle_play_event(event)
            elif self.state in ("garage", "maps"):
                self.handle_browse_event(event)
            else:
                self.handle_menu_event(event)

    def handle_play_event(self, event):
        """One-shot keys during play: pause, restart and jump."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.set_state("paused")
            elif event.key == pygame.K_r:
                self.start_run()
            elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                self.rickshaw.jump()

    def handle_menu_event(self, event):
        """Pass the event to the current menu and apply shortcuts (Esc, R)."""
        action = self.menus[self.state].handle_event(event)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                action = {"paused": "resume", "help": "menu", "options": "menu"}.get(self.state, action)
            elif event.key == pygame.K_r and self.state in ("paused", "gameover"):
                action = "restart"
        if action:
            self.do_action(action)

    def handle_browse_event(self, event):
        """Garage/map screens: arrows browse, Enter confirms, Esc goes back, buttons work with the mouse."""
        action = None
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                action = "prev"
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                action = "next"
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                action = "act"
            elif event.key == pygame.K_ESCAPE:
                action = "menu"
        else:
            action = self.menus[self.state].handle_event(event)
        if action:
            self.do_action(action)

    def do_action(self, action):
        """Carry out a menu action string such as 'start', 'resume' or 'exit'."""
        if action == "restart":
            self.start_run()
        elif action == "resume":
            self.state = "playing"
        elif action == "start":
            self.set_state("maps")
        elif action in ("menu", "help", "options", "garage"):
            self.set_state(action)
        elif action in ("prev", "next"):
            self.browse(-1 if action == "prev" else 1)
        elif action == "act":
            self.browse_confirm()
        elif action == "toggle_fps":
            self.show_fps = not self.show_fps
        elif action == "exit":
            self.running = False

    def browse(self, step):
        """Move to the previous/next vehicle (garage) or map (map screen)."""
        if self.state == "garage":
            self.g_idx = (self.g_idx + step) % len(vehicles.VEHICLES)
            self.message = ("", 0.0)
        else:
            self.m_idx = (self.m_idx + step) % len(maps.MAPS)
            self.apply_map(maps.MAPS[self.m_idx])

    def browse_confirm(self):
        """Garage: buy or select the shown vehicle. Map screen: choose the map and start driving."""
        if self.state == "maps":
            self.save["map"] = maps.MAPS[self.m_idx]["id"]
            self.persist()
            self.start_run()
            return
        spec = vehicles.VEHICLES[self.g_idx]
        if spec["id"] not in self.save["owned"]:
            if self.save["wallet"] < spec["price"]:
                self.message = (f"Not enough rupees! You need {money(spec['price'] - self.save['wallet'])} more.", 2.5)
                return
            self.save["wallet"] -= spec["price"]
            self.save["owned"].append(spec["id"])
        self.save["vehicle"] = spec["id"]
        self.persist()

    # ---- update (fixed physics step, only while playing) ----
    def update(self, dt):
        """One physics step: move the vehicle, obstacles, particles, camera and check the end-of-run rules."""
        if self.state != "playing":
            return
        r = self.rickshaw
        r.update(dt, pygame.key.get_pressed(), self.fx)
        self.hazards.update(r, dt, self.fx)
        self.fx.update(dt)

        # Camera eases toward a point slightly ahead of the vehicle (smooth follow + look-ahead)
        target = r.x - S.WIDTH * 0.35 + r.speed * S.CAMERA_LOOKAHEAD
        self.camera_x += (target - self.camera_x) * min(1.0, S.CAMERA_SMOOTH * dt)

        # Landing/crash impacts become screen shake that fades out
        if r.impact:
            self.shake = max(self.shake, r.impact)
            r.impact = 0.0
        self.shake *= math.exp(-S.SHAKE_DECAY * dt)

        if r.health <= 0:
            self.end_run("WRECKED!")
        elif r.fuel <= 0:
            self.dry_time += dt
            if r.on_ground and (abs(r.speed) < 5 or self.dry_time > S.OUT_OF_FUEL_GRACE):
                self.end_run("OUT OF CNG!")

    # ---- drawing ----
    def draw_background(self, surf, scroll):
        """Tile the skyline horizontally; `scroll` is already scaled for parallax."""
        w = self.background.get_width()
        x = -(scroll % w)
        while x < S.WIDTH:
            surf.blit(self.background, (x, 0))
            x += w

    def draw_road(self, surf, cam):
        """Draw the road in the map's colours: body, darker lane, dashed centre line, pebbles and a bright edge."""
        m = terrain.current()
        top = [(sx, terrain.get_height(sx + cam)) for sx in range(0, S.WIDTH + 12, 10)]
        pygame.draw.polygon(surf, m["road"], [(0, S.HEIGHT)] + top + [(S.WIDTH, S.HEIGHT)])
        band = [(x, y + 8) for x, y in top] + [(x, y + 30) for x, y in reversed(top)]
        pygame.draw.polygon(surf, m["asphalt"], band)
        first = int(cam // 90) * 90
        for wx in range(first, int(cam) + S.WIDTH + 90, 90):             # dashes scroll with the world
            a = (wx - cam, terrain.get_height(wx) + 19)
            b = (wx + 40 - cam, terrain.get_height(wx + 40) + 19)
            pygame.draw.line(surf, (235, 225, 190), a, b, 3)
        first = int(cam // 37) * 37
        for wx in range(first, int(cam) + S.WIDTH + 37, 37):             # pebbles in the dirt below
            py = terrain.get_height(wx) + 40 + (wx * 31) % 60
            pygame.draw.circle(surf, tuple(max(0, c - 25) for c in m["road"]), (int(wx - cam), int(py)), 2 + (wx % 3))
        pygame.draw.lines(surf, m["road_top"], False, top, 4)

    def draw(self):
        """Draw world layers back-to-front, apply shake, then HUD, menus and overlays."""
        in_game = self.state in PLAY_STATES
        cam = self.camera_x if in_game else self.menu_scroll
        w = self.world
        self.draw_background(w, cam * S.BG_PARALLAX)
        self.clouds.draw(w, cam, self.time)
        self.scenery.draw(w, cam, self.time)
        self.draw_road(w, cam)
        if in_game:
            self.hazards.draw_ground_marks(w, cam, self.time)
            self.hazards.draw(w, cam, self.time)
            self.fx.draw(w, cam)
            self.rickshaw.draw(w, cam)
            effects.draw_speed_lines(w, abs(self.rickshaw.speed) / self.rickshaw.spec["max_speed"])

        # Screen shake: shift the finished world picture by a random amount
        off = (0, 0)
        if self.state == "playing" and self.shake > 0.3:
            s = int(self.shake)
            off = (random.randint(-s, s), random.randint(-s, s))
        self.screen.fill(SKY)
        self.screen.blit(w, off)

        if in_game:
            self.hud.draw(self.screen, self.rickshaw, self.distance(), self.time)
        if self.state in DIM_STATES:
            self.screen.blit(self.dim, (0, 0))

        {"menu": self.draw_main_menu, "help": self.draw_help, "options": self.draw_options,
         "paused": self.draw_pause, "gameover": self.draw_gameover,
         "garage": self.draw_garage, "maps": self.draw_maps}.get(self.state, lambda: None)()

        if self.show_fps:
            ui.draw_text(self.screen, f"{self.clock.get_fps():.0f} FPS", self.fonts.tiny,
                         S.WHITE, (S.WIDTH // 2, 14))
        pygame.display.flip()

    def draw_main_menu(self):
        """Title banner, wallet, main buttons and footer."""
        ui.draw_title_banner(self.screen, self.fonts, self.title_icon)
        ui.draw_text(self.screen, money(self.save["wallet"]), self.fonts.mid, S.MARIGOLD, (S.WIDTH - 24, 24), "midright")
        self.menus["menu"].draw(self.screen, self.fonts)
        ui.draw_text(self.screen, "ITFA Project  |  Python + Pygame", self.fonts.tiny,
                     S.WHITE, (S.WIDTH // 2, S.HEIGHT - 18))

    def draw_help(self):
        """How-to-play panel listing the controls and the new road hazards."""
        panel = pygame.Rect(0, 0, 640, 500)
        panel.midtop = (S.WIDTH // 2, 40)
        ui.draw_panel(self.screen, self.fonts, panel, "HOW TO PLAY")
        y = panel.top + 105
        for key, what in HELP_LINES:
            ui.draw_text(self.screen, key, self.fonts.small, S.MARIGOLD, (panel.left + 70, y), "midleft")
            ui.draw_text(self.screen, what, self.fonts.small, S.WHITE, (panel.left + 290, y), "midleft")
            y += 34
        tips = [(f"Collect coins (Rs {S.COIN_VALUE} each) and CNG cylinders.", S.WHITE),
                ("Rocks, carts and cars are solid: jump them!", S.WHITE),
                ("Barrels, cones and barricades can be smashed.", S.WHITE),
                ("Wheels only grip the road, so you can't drive in mid-air!", S.LIME)]
        for i, (line, col) in enumerate(tips):
            ui.draw_text(self.screen, line, self.fonts.small, col, (panel.centerx, panel.top + 292 + i * 30), max_width=580)
        self.menus["help"].draw(self.screen, self.fonts)

    def draw_options(self):
        """Options panel with an ON/OFF toggle."""
        panel = pygame.Rect(0, 0, 500, 300)
        panel.midtop = (S.WIDTH // 2, 100)
        ui.draw_panel(self.screen, self.fonts, panel, "OPTIONS")
        self.menus["options"].set_labels([f"SHOW FPS: {'ON' if self.show_fps else 'OFF'}", "BACK"])
        self.menus["options"].draw(self.screen, self.fonts)

    def draw_pause(self):
        """Pause panel."""
        panel = pygame.Rect(0, 0, 400, 340)
        panel.midtop = (S.WIDTH // 2, 115)
        ui.draw_panel(self.screen, self.fonts, panel, "PAUSED")
        self.menus["paused"].draw(self.screen, self.fonts)

    def draw_gameover(self):
        """Result panel with distance, coins earned, best score and retry buttons."""
        res = self.result
        panel = pygame.Rect(0, 0, 460, 420)
        panel.midtop = (S.WIDTH // 2, 70)
        ui.draw_panel(self.screen, self.fonts, panel, res["reason"])
        cx = panel.centerx
        ui.draw_text(self.screen, "DISTANCE TRAVELLED", self.fonts.tiny, S.MARIGOLD, (cx, 165), shadow=False)
        ui.draw_text(self.screen, f"{int(res['dist'])} m", self.fonts.title, S.WHITE, (cx, 207))
        best = self.save["best"].get(self.selected_map()["id"], 0)
        ui.draw_text(self.screen, f"Best: {int(best)} m", self.fonts.small, S.WHITE, (cx, 250))
        ui.draw_text(self.screen, f"Coins: {res['coins']}   +{money(res['earned'])}", self.fonts.small, S.MARIGOLD, (cx, 282))
        ui.draw_text(self.screen, f"Wallet: {money(self.save['wallet'])}", self.fonts.small, S.WHITE, (cx, 308))
        if res["record"]:
            ui.draw_text(self.screen, "NEW RECORD!", self.fonts.mid, S.LIME, (cx, 336))
        self.menus["gameover"].draw(self.screen, self.fonts)

    def draw_stat_bar(self, label, frac, x, y):
        """One labelled horizontal bar (used for the vehicle stats)."""
        ui.draw_text(self.screen, label, self.fonts.tiny, S.MARIGOLD, (x, y), "midleft", shadow=False)
        bar = pygame.Rect(x + 90, y - 8, 230, 16)
        pygame.draw.rect(self.screen, S.PK_GREEN_DARK, bar, border_radius=4)
        pygame.draw.rect(self.screen, S.LIME if frac > 0.6 else S.MARIGOLD, (bar.left, bar.top, int(bar.width * frac), bar.height), border_radius=4)
        pygame.draw.rect(self.screen, S.WHITE, bar, 1, border_radius=4)

    def draw_garage(self):
        """Garage screen: shows one vehicle with turning wheels, its stats, price and a buy/select button."""
        spec = vehicles.VEHICLES[self.g_idx]
        art = self.preview_arts[spec["id"]]
        panel = pygame.Rect(40, 25, 920, 550)
        ui.draw_panel(self.screen, self.fonts, panel, "GARAGE")
        ui.draw_text(self.screen, money(self.save["wallet"]), self.fonts.mid, S.MARIGOLD, (panel.right - 40, panel.top + 45), "midright")

        box = pygame.Rect(75, 115, 430, 300)                           # showroom window
        pygame.draw.rect(self.screen, (255, 226, 170), box, border_radius=14)
        pygame.draw.rect(self.screen, (70, 62, 56), (box.left, box.bottom - 70, box.width, 70),
                         border_bottom_left_radius=14, border_bottom_right_radius=14)
        pygame.draw.rect(self.screen, S.MARIGOLD, box, 4, border_radius=14)
        ground = box.bottom - 58
        top = ground - (art.rear_img[1] + art.r_rear)                  # place the tyre bottoms on the floor
        art.draw_preview(self.screen, (box.centerx, top + art.height / 2), self.time)

        x = 540
        ui.draw_text(self.screen, spec["name"], self.fonts.mid, S.MARIGOLD, (x, 135), "midleft", max_width=400)
        for i, line in enumerate(ui.wrap_text(self.fonts.small, spec["blurb"], 390)[:3]):
            ui.draw_text(self.screen, line, self.fonts.small, S.WHITE, (x, 172 + i * 24), "midleft", shadow=False)
        fr = vehicles.stat_fractions(spec)
        for i, (label, key) in enumerate((("SPEED", "speed"), ("ACCEL", "accel"), ("FUEL", "fuel"), ("ARMOR", "armor"))):
            self.draw_stat_bar(label, fr[key], x, 275 + i * 34)

        owned = spec["id"] in self.save["owned"]
        chosen = self.save["vehicle"] == spec["id"]
        if chosen:
            ui.draw_text(self.screen, "SELECTED", self.fonts.mid, S.LIME, (x, 440), "midleft")
        elif owned:
            ui.draw_text(self.screen, "OWNED", self.fonts.mid, S.WHITE, (x, 440), "midleft")
        else:
            ui.draw_text(self.screen, money(spec["price"]), self.fonts.mid, S.MARIGOLD, (x, 440), "midleft")
        text, left = self.message
        if left > 0:
            ui.draw_text(self.screen, text, self.fonts.small, S.RED, (panel.centerx, 465), max_width=800)
        label = "SELECTED" if chosen else ("SELECT" if owned else f"BUY {money(spec['price'])}")
        self.menus["garage"].set_labels(["<", label, ">", "BACK"])
        self.menus["garage"].draw(self.screen, self.fonts)

    def draw_maps(self):
        """Map screen: skyline preview, road description, difficulty and best distance."""
        m = maps.MAPS[self.m_idx]
        panel = pygame.Rect(40, 25, 920, 550)
        ui.draw_panel(self.screen, self.fonts, panel, "CHOOSE YOUR ROAD")
        box = pygame.Rect(75, 125, 430, 258)
        self.screen.blit(self.map_thumb[m["id"]], box)
        pygame.draw.rect(self.screen, S.MARIGOLD, box, 4, border_radius=6)

        x = 540
        ui.draw_text(self.screen, m["name"], self.fonts.mid, S.MARIGOLD, (x, 140), "midleft", max_width=400)
        ui.draw_text(self.screen, m["tagline"], self.fonts.small, S.LIME, (x, 176), "midleft", max_width=400)
        for i, line in enumerate(m["lines"]):
            for j, part in enumerate(ui.wrap_text(self.fonts.small, line, 390)):
                ui.draw_text(self.screen, part, self.fonts.small, S.WHITE, (x, 214 + (i * 2 + j) * 24), "midleft", shadow=False)
        ui.draw_text(self.screen, "DIFFICULTY", self.fonts.tiny, S.MARIGOLD, (x, 332), "midleft", shadow=False)
        for i in range(3):
            ui.diamond(self.screen, (x + 110 + i * 26, 332), 9, S.RED if i < m["difficulty"] else S.PK_GREEN_DARK)
        best = self.save["best"].get(m["id"], 0)
        ui.draw_text(self.screen, f"BEST: {int(best)} m", self.fonts.small, S.WHITE, (x, 366), "midleft")
        vname = vehicles.BY_ID[self.save["vehicle"]]["name"]
        ui.draw_text(self.screen, f"DRIVING: {vname}", self.fonts.small, S.MARIGOLD, (panel.centerx, 440), max_width=800)
        self.menus["maps"].set_labels(["<", "DRIVE!", ">", "BACK"])
        self.menus["maps"].draw(self.screen, self.fonts)

    # ---- main loop ----
    def run(self):
        """Main loop: events -> fixed-step physics (120 Hz) -> draw, until the player quits."""
        accumulator = 0.0
        while self.running:
            frame_time = min(self.clock.tick(S.FPS) / 1000, 0.1)
            self.time += frame_time
            self.message = (self.message[0], max(0.0, self.message[1] - frame_time))
            self.handle_events()
            if self.state == "playing":
                accumulator += frame_time
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
