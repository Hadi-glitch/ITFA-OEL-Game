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
import assets
import sound
import powerups

PLAY_STATES = ("playing", "paused", "gameover")
DIM_STATES = ("paused", "gameover", "garage", "maps", "shop")
SKY = (255, 205, 140)          # fills the screen edges while the screen shakes
ROAD_STEP = 3     # width of one painted road column in px (the road PNG's width must be a multiple of this)
ROAD_LIFT = 1     # px the painted asphalt edge sits above terrain height

HELP_LINES = [
    ("D / Right", "Accelerate"),
    ("A / Left", "Brake and reverse"),
    ("Space / W / Up", "Jump"),
    ("R", "Restart the run"),
    ("Esc", "Pause"),
]

VOLUME_STEPS = [0.0, 0.3, 0.6, 1.0]
VOLUME_NAMES = ["OFF", "LOW", "MED", "HIGH"]
MILESTONES = [100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000, 10000]


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
        sound.init()
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        pygame.display.set_caption(S.TITLE)
        self.clock = pygame.time.Clock()
        self.fonts = ui.Fonts()
        self.hud = ui.HUD(self.fonts)
        self.title_icon = ui.make_crescent_star(96)
        self.world = pygame.Surface((S.WIDTH, S.HEIGHT))    # the world is drawn here, then shaken onto the screen
        self.save = save.reset()   # resets game data on startup when run again
        self.arts = {v["id"]: vehicles.VehicleArt(v) for v in vehicles.VEHICLES}                 # in-game sprites
        self.preview_arts = {v["id"]: vehicles.VehicleArt(v, 1.35) for v in vehicles.VEHICLES}   # bigger, for the garage
        self.map_bg = {m["id"]: maps.build_background(m) for m in maps.MAPS}
        self.map_thumb = {m["id"]: self.make_thumb(m) for m in maps.MAPS}
        self.road_tex = {m["id"]: assets.load_image("roads", f"{m['id']}.png") for m in maps.MAPS}
        self.rickshaw = None                                # created when a run starts
        self.fx = effects.ParticleSystem()
        self.clouds = effects.Clouds()
        self.scenery = effects.Scenery()
        self.hazards = Hazards()
        self.flash = effects.ScreenFlash()
        self.milestones_shown = set()
        self.milestone_display = None
        self.dim = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
        for y in range(S.HEIGHT):
            t = y / S.HEIGHT
            alpha = int(120 + 55 * t)
            pygame.draw.line(self.dim, (0, 0, 0, alpha), (0, y), (S.WIDTH, y))

        cx = S.WIDTH // 2
        browse = [("<", "prev"), ("", "act"), (">", "next"), ("BACK", "menu")]
        self.menus = {
            "menu": ui.Menu([("START", "start"), ("GARAGE", "garage"), ("SHOP", "shop"),
                             ("HOW TO PLAY", "help"), ("OPTIONS", "options"),
                             ("EXIT", "exit")], cx, 210, height=44, gap=7),
            "help": ui.Menu([("BACK", "menu")], cx, 490),
            "options": ui.Menu([("RESET GAME DATA", "reset_save"),
                                ("", "toggle_sfx"), ("", "toggle_music"), ("", "toggle_fps"),
                                ("BACK", "menu")], cx, 140, width=380, gap=8),
            "paused": ui.Menu([("RESUME", "resume"), ("RESTART", "restart"),
                               ("MAIN MENU", "menu")], cx, 210),
            "gameover": ui.Menu([("RETRY", "restart"), ("MAIN MENU", "menu")], cx, 350),
            "garage": ui.Menu(browse, cx, 487, width=150, height=48, gap=12, horizontal=True),
            "maps": ui.Menu(list(browse), cx, 487, width=150, height=48, gap=12, horizontal=True),
            "shop": ui.Menu(list(browse), cx, 487, width=150, height=48, gap=12, horizontal=True),
        }
        self.state = "menu"
        self.running = True
        self.show_fps = False
        self.camera_x = 0.0
        self.menu_scroll = 0.0
        self.shake = 0.0
        self.time = 0.0
        self.dry_time = 0.0
        self.low_fuel_timer = 0.0
        self.g_idx = 0                    # vehicle being browsed in the garage
        self.m_idx = 0                    # map being browsed
        self.s_idx = 0                    # powerup being browsed in the shop
        self.message = ("", 0.0)          # (text, seconds left) shown in the garage
        self.result = {}
        self.background = None
        self.apply_map(maps.BY_ID.get(self.save["map"], maps.MAPS[0]))
        sound.discover_music()
        sound.play_music()

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
        elif state == "shop":
            self.s_idx = 0
            self.menus[state].selected = 1
            self.message = ("", 0.0)
        if state in ("menu", "help", "options", "garage", "shop"):
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
        self.low_fuel_timer = 0.0
        self.milestones_shown = set()
        self.milestone_display = None
        self.rickshaw.powerups.set_levels(self.save.get("powerup_levels", {}))
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
        sound.play("record" if self.result["record"] else "gameover")
        self.set_state("gameover")

    # ---- events ----
    def handle_events(self):
        """Read the OS event queue and route each event to play, browse or menu handling."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.state == "playing":
                self.handle_play_event(event)
            elif self.state in ("garage", "maps", "shop"):
                self.handle_browse_event(event)
            else:
                self.handle_menu_event(event)

    def handle_play_event(self, event):
        """One-shot keys during play: pause, restart and jump."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                sound.play("click")
                self.set_state("paused")
            elif event.key == pygame.K_r:
                self.start_run()
            elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                if self.rickshaw.on_ground:                 # the jump only works on the ground
                    sound.play("jump")
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
        sound.play("click")
        if action == "restart":
            self.start_run()
        elif action == "resume":
            self.state = "playing"
        elif action == "start":
            self.set_state("maps")
        elif action in ("menu", "help", "options", "garage", "shop"):
            self.set_state(action)
        elif action in ("prev", "next"):
            self.browse(-1 if action == "prev" else 1)
        elif action == "act":
            self.browse_confirm()
        elif action == "reset_save":
            self.save = save.reset()
            self.g_idx = 0
            self.m_idx = 0
            self.s_idx = 0
            self.apply_map(self.selected_map())
            self.message = ("Game data reset successfully!", 2.5)
            sound.play("buy")
        elif action == "toggle_fps":
            self.show_fps = not self.show_fps
        elif action == "toggle_sfx":
            idx = min(range(len(VOLUME_STEPS)), key=lambda i: abs(VOLUME_STEPS[i] - S.SFX_VOLUME))
            S.SFX_VOLUME = VOLUME_STEPS[(idx + 1) % len(VOLUME_STEPS)]
        elif action == "toggle_music":
            idx = min(range(len(VOLUME_STEPS)), key=lambda i: abs(VOLUME_STEPS[i] - S.MUSIC_VOLUME))
            S.MUSIC_VOLUME = VOLUME_STEPS[(idx + 1) % len(VOLUME_STEPS)]
            sound.set_music_volume(S.MUSIC_VOLUME)
        elif action == "exit":
            self.running = False

    def browse(self, step):
        """Move to the previous/next vehicle (garage) or map (map screen)."""
        if self.state == "garage":
            self.g_idx = (self.g_idx + step) % len(vehicles.VEHICLES)
            self.message = ("", 0.0)
        elif self.state == "shop":
            self.s_idx = (self.s_idx + step) % len(powerups.POWERUPS)
            self.message = ("", 0.0)
        else:
            self.m_idx = (self.m_idx + step) % len(maps.MAPS)
            self.apply_map(maps.MAPS[self.m_idx])

    def browse_confirm(self):
        """Garage: buy or select the shown vehicle. Map screen: choose the map and start driving."""
        if self.state == "maps":
            if not maps.is_unlocked(self.m_idx, self.save["best"]):
                prev_name, req = maps.unlock_info(self.m_idx)
                self.message = (f"Locked! Reach {req} m on {prev_name} first.", 2.5)
                sound.play("error")
                return
            self.save["map"] = maps.MAPS[self.m_idx]["id"]
            self.persist()
            self.start_run()
            return
        if self.state == "shop":
            self.shop_upgrade()
            return
        spec = vehicles.VEHICLES[self.g_idx]
        if spec["id"] not in self.save["owned"]:
            if self.save["wallet"] < spec["price"]:
                self.message = (f"Not enough rupees! You need {money(spec['price'] - self.save['wallet'])} more.", 2.5)
                sound.play("error")
                return
            self.save["wallet"] -= spec["price"]
            self.save["owned"].append(spec["id"])
            sound.play("buy")
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

        # Powerup flash
        if r.pending_flash:
            self.flash.trigger(*r.pending_flash)
            r.pending_flash = None

        # Milestones
        d = self.distance()
        for m in MILESTONES:
            if d >= m and m not in self.milestones_shown:
                self.milestones_shown.add(m)
                self.milestone_display = (f"{m} m!", 2.0)
                self.flash.trigger(S.LIME, 40)
                break
        if self.milestone_display:
            text, timer = self.milestone_display
            timer -= dt
            self.milestone_display = (text, timer) if timer > 0 else None
        self.flash.update(dt)

        if 0 < r.fuel <= r.fuel_max * 0.25:                 # beep once a second while the tank is low
            self.low_fuel_timer -= dt
            if self.low_fuel_timer <= 0:
                sound.play("low_fuel")
                self.low_fuel_timer = 1.0

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
        """Road: painted strip if assets/roads/<map id>.png exists, otherwise the shape-drawn road."""
        m = terrain.current()
        tex = self.road_tex.get(m["id"])
        top = [(sx, terrain.get_height(sx + cam)) for sx in range(0, S.WIDTH + 12, 10)]
        pygame.draw.polygon(surf, m["road"], [(0, S.HEIGHT)] + top + [(S.WIDTH, S.HEIGHT)])   # also backs the texture
        if tex:
            self.draw_road_texture(surf, cam, tex)
        else:
            band = [(x, y + 8) for x, y in top] + [(x, y + 30) for x, y in reversed(top)]
            pygame.draw.polygon(surf, m["asphalt"], band)
        first = int(cam // 90) * 90
        for wx in range(first, int(cam) + S.WIDTH + 90, 90):             # dashes scroll with the world
            a = (wx - cam, terrain.get_height(wx) + 19)
            b = (wx + 40 - cam, terrain.get_height(wx + 40) + 19)
            pygame.draw.line(surf, (235, 225, 190), a, b, 3)
        if not tex:
            first = int(cam // 37) * 37
            for wx in range(first, int(cam) + S.WIDTH + 37, 37):         # pebbles in the dirt below
                py = terrain.get_height(wx) + 40 + (wx * 31) % 60
                pygame.draw.circle(surf, tuple(max(0, c - 25) for c in m["road"]), (int(wx - cam), int(py)), 2 + (wx % 3))
            pygame.draw.lines(surf, m["road_top"], False, top, 4)

        # 3D Curb Edge: raised curb highlight and depth shadow
        curb_pts = [(sx, terrain.get_height(sx + cam) - 1) for sx in range(0, S.WIDTH + 12, 10)]
        pygame.draw.lines(surf, (245, 240, 225), False, curb_pts, 2)
        curb_shadow = [(sx, terrain.get_height(sx + cam) + 2) for sx in range(0, S.WIDTH + 12, 10)]
        pygame.draw.lines(surf, (30, 28, 25), False, curb_shadow, 1)

    def draw_road_texture(self, surf, cam, tex):
        """Paint the road PNG as thin vertical strips, each moved up/down to follow terrain.get_height."""
        tw, th = tex.get_size()
        icam = int(cam)
        first = int(cam // ROAD_STEP) * ROAD_STEP
        for wx in range(first, icam + S.WIDTH + ROAD_STEP, ROAD_STEP):
            y = terrain.get_height(wx + ROAD_STEP / 2) - ROAD_LIFT
            surf.blit(tex, (wx - icam, y), (wx % tw, 0, ROAD_STEP, th))

    def draw(self):
        """Draw world layers back-to-front, apply shake, then HUD, menus and overlays."""
        in_game = self.state in PLAY_STATES
        cam = self.camera_x if in_game else self.menu_scroll
        w = self.world
        self.draw_background(w, cam * S.BG_PARALLAX)
        self.clouds.draw(w, cam, self.time)
        self.scenery.draw(w, cam, self.time)
        self.draw_road(w, cam)
        if in_game and self.rickshaw is not None:
            effects.draw_heat_shimmer(w, self.time, 0.35)
            effects.draw_road_depth(w, cam, self.time)
            self.hazards.draw_ground_marks(w, cam, self.time)
            self.hazards.draw(w, cam, self.time)
            self.fx.draw(w, cam)
            self.rickshaw.draw(w, cam)

        # Screen shake: shift the finished world picture by a random amount
        off = (0, 0)
        if self.state == "playing" and self.shake > 0.3:
            s = int(self.shake)
            off = (random.randint(-s, s), random.randint(-s, s))
        self.screen.fill(SKY)
        self.screen.blit(w, off)

        if in_game and self.rickshaw is not None:
            effects.draw_vignette(self.screen)
            self.hud.draw(self.screen, self.rickshaw, self.distance(), self.time)
            self.hud.draw_active_powerups(self.screen, self.rickshaw.powerups.active_list, self.time)
            health_frac = self.rickshaw.health / self.rickshaw.spec["armor"]
            effects.draw_low_health_warning(self.screen, health_frac, self.time)
            if self.milestone_display:
                ui.draw_text(self.screen, self.milestone_display[0], self.fonts.big,
                             S.LIME, (S.WIDTH // 2, S.HEIGHT // 2 - 80))
        self.flash.draw(self.screen)
        if self.state in DIM_STATES:
            self.screen.blit(self.dim, (0, 0))

        {"menu": self.draw_main_menu, "help": self.draw_help, "options": self.draw_options,
         "paused": self.draw_pause, "gameover": self.draw_gameover,
         "garage": self.draw_garage, "maps": self.draw_maps,
         "shop": self.draw_shop}.get(self.state, lambda: None)()

        if self.show_fps:
            ui.draw_text(self.screen, f"{self.clock.get_fps():.0f} FPS", self.fonts.tiny,
                         S.WHITE, (S.WIDTH // 2, 14))
        pygame.display.flip()

    def draw_main_menu(self):
        """Title banner, 3D glass wallet badge, main buttons and footer."""
        ui.draw_title_banner(self.screen, self.fonts, self.title_icon)
        # 3D Glass Wallet Badge
        wallet_str = money(self.save["wallet"])
        wb_w = max(145, len(wallet_str) * 14 + 50)
        wallet_rect = pygame.Rect(S.WIDTH - wb_w - 20, 18, wb_w, 42)
        ui.draw_glass_rect(self.screen, wallet_rect, S.PK_GREEN_DARK, alpha=200, border_color=S.MARIGOLD, border_radius=10)
        cx_coin = wallet_rect.left + 22
        cy_coin = wallet_rect.centery
        pygame.draw.circle(self.screen, (150, 95, 0), (cx_coin + 1, cy_coin + 1), 11)
        pygame.draw.circle(self.screen, S.MARIGOLD, (cx_coin, cy_coin), 10)
        pygame.draw.circle(self.screen, (255, 230, 110), (cx_coin - 2, cy_coin - 2), 4)
        ui.draw_text(self.screen, wallet_str, self.fonts.mid, S.MARIGOLD, (wallet_rect.right - 14, wallet_rect.centery), "midright")
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
                ("Glowing diamonds are powerups: speed, shield, magnet and more!", S.LIME),
                ("Wheels only grip the road, so you can't drive in mid-air!", S.LIME)]
        for i, (line, col) in enumerate(tips):
            ui.draw_text(self.screen, line, self.fonts.small, col, (panel.centerx, panel.top + 280 + i * 28), max_width=580)
        self.menus["help"].draw(self.screen, self.fonts)

    def draw_options(self):
        """Options panel with volume, display and reset toggles."""
        panel = pygame.Rect(0, 0, 520, 440)
        panel.midtop = (S.WIDTH // 2, 50)
        ui.draw_panel(self.screen, self.fonts, panel, "OPTIONS")
        sfx_name = VOLUME_NAMES[min(range(len(VOLUME_STEPS)), key=lambda i: abs(VOLUME_STEPS[i] - S.SFX_VOLUME))]
        mus_name = VOLUME_NAMES[min(range(len(VOLUME_STEPS)), key=lambda i: abs(VOLUME_STEPS[i] - S.MUSIC_VOLUME))]
        self.menus["options"].set_labels(["RESET GAME DATA",
                                          f"SFX VOLUME: {sfx_name}", f"MUSIC: {mus_name}",
                                          f"SHOW FPS: {'ON' if self.show_fps else 'OFF'}", "BACK"])
        self.menus["options"].draw(self.screen, self.fonts)
        text, left = self.message
        if left > 0:
            ui.draw_text(self.screen, text, self.fonts.small, S.LIME, (panel.centerx, panel.bottom - 42))

    def draw_pause(self):
        """Pause panel."""
        panel = pygame.Rect(0, 0, 400, 340)
        panel.midtop = (S.WIDTH // 2, 115)
        ui.draw_panel(self.screen, self.fonts, panel, "PAUSED")
        self.menus["paused"].draw(self.screen, self.fonts)

    def draw_gameover(self):
        """Result panel with distance, coins earned, best score and retry buttons - 3D styled."""
        res = self.result
        panel = pygame.Rect(0, 0, 460, 420)
        panel.midtop = (S.WIDTH // 2, 70)
        ui.draw_panel(self.screen, self.fonts, panel, res["reason"])
        cx = panel.centerx
        ui.draw_text(self.screen, "DISTANCE TRAVELLED", self.fonts.tiny, S.MARIGOLD, (cx, 165), shadow=False)
        # Golden glowing distance
        ui.draw_text(self.screen, f"{int(res['dist'])} m", self.fonts.title, (255, 230, 150), (cx, 206))
        ui.draw_text(self.screen, f"{int(res['dist'])} m", self.fonts.title, S.WHITE, (cx, 207))
        best = self.save["best"].get(self.selected_map()["id"], 0)
        ui.draw_text(self.screen, f"Best: {int(best)} m", self.fonts.small, S.WHITE, (cx, 248))
        # 3D separator line
        pygame.draw.line(self.screen, (0, 0, 0, 100), (cx - 130, 269), (cx + 130, 269), 2)
        pygame.draw.line(self.screen, S.MARIGOLD, (cx - 130, 268), (cx + 130, 268), 1)
        ui.draw_text(self.screen, f"Coins: {res['coins']}   +{money(res['earned'])}", self.fonts.small, S.MARIGOLD, (cx, 285))
        ui.draw_text(self.screen, f"Wallet: {money(self.save['wallet'])}", self.fonts.small, S.WHITE, (cx, 310))
        if res["record"]:
            ui.draw_text(self.screen, "NEW RECORD!", self.fonts.mid, (200, 255, 140), (cx, 337))
            ui.draw_text(self.screen, "NEW RECORD!", self.fonts.mid, S.LIME, (cx, 336))
        self.menus["gameover"].draw(self.screen, self.fonts)

    def draw_stat_bar(self, label, frac, x, y):
        """3D embossed stat bar with gradient fill and gloss highlight."""
        ui.draw_text(self.screen, label, self.fonts.tiny, S.MARIGOLD, (x, y), "midleft", shadow=False)
        bar = pygame.Rect(x + 90, y - 9, 230, 18)
        # 3D groove background
        pygame.draw.rect(self.screen, (2, 20, 10), bar, border_radius=5)
        pygame.draw.rect(self.screen, (0, 0, 0, 140), bar.inflate(-2, -2), border_radius=4)
        
        fill_w = int((bar.width - 4) * max(0.0, min(1.0, frac)))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar.left + 2, bar.top + 2, fill_w, bar.height - 4)
            base_col = S.LIME if frac > 0.6 else S.MARIGOLD
            pygame.draw.rect(self.screen, base_col, fill_rect, border_radius=4)
            # 3D Top specular highlight
            hi_col = tuple(min(255, c + 70) for c in base_col)
            pygame.draw.rect(self.screen, hi_col, (fill_rect.left + 1, fill_rect.top + 1, fill_rect.width - 2, fill_rect.height // 2), border_radius=2)
            # 3D Bottom shadow
            lo_col = tuple(max(0, c - 50) for c in base_col)
            pygame.draw.line(self.screen, lo_col, (fill_rect.left, fill_rect.bottom - 1), (fill_rect.right - 1, fill_rect.bottom - 1))
            
        # 3D Chrome Frame
        pygame.draw.rect(self.screen, (100, 100, 100), bar, 1, border_radius=5)
        pygame.draw.rect(self.screen, (255, 255, 255, 80), (bar.left, bar.top, bar.width, 1))

    def draw_garage(self):
        """Garage screen: 3D showroom stage, rotating preview, stats, price and action button."""
        spec = vehicles.VEHICLES[self.g_idx]
        art = self.preview_arts[spec["id"]]
        panel = pygame.Rect(40, 25, 920, 550)
        ui.draw_panel(self.screen, self.fonts, panel, "GARAGE")
        
        # 3D Glass Wallet Badge in Garage
        wallet_str = money(self.save["wallet"])
        wb_w = max(145, len(wallet_str) * 14 + 50)
        wallet_rect = pygame.Rect(panel.right - wb_w - 30, panel.top + 24, wb_w, 40)
        ui.draw_glass_rect(self.screen, wallet_rect, S.PK_GREEN_DARK, alpha=200, border_color=S.MARIGOLD, border_radius=10)
        cx_coin = wallet_rect.left + 20
        cy_coin = wallet_rect.centery
        pygame.draw.circle(self.screen, (150, 95, 0), (cx_coin + 1, cy_coin + 1), 10)
        pygame.draw.circle(self.screen, S.MARIGOLD, (cx_coin, cy_coin), 9)
        pygame.draw.circle(self.screen, (255, 230, 110), (cx_coin - 2, cy_coin - 2), 3)
        ui.draw_text(self.screen, wallet_str, self.fonts.mid, S.MARIGOLD, (wallet_rect.right - 14, wallet_rect.centery), "midright")

        # 3D Showroom Stage Window
        box = pygame.Rect(75, 115, 430, 300)
        showroom = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        for y in range(box.height):
            t = y / max(1, box.height)
            r = int(255 - 45 * t)
            g = int(228 - 55 * t)
            b = int(175 - 45 * t)
            pygame.draw.line(showroom, (r, g, b, 255), (0, y), (box.width, y))
        mask = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, box.width, box.height), border_radius=14)
        showroom.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(showroom, box.topleft)

        # 3D Spotlight Beam from ceiling
        spot_surf = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        pygame.draw.polygon(spot_surf, (255, 255, 255, 22),
                            [(box.width // 2 - 40, 0), (box.width // 2 + 40, 0),
                             (box.width - 20, box.height - 70), (20, box.height - 70)])
        spot_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(spot_surf, box.topleft)

        # Stage Floor with metallic reflection gradient
        floor_h = 70
        floor = pygame.Surface((box.width, floor_h), pygame.SRCALPHA)
        for y in range(floor_h):
            t = y / max(1, floor_h)
            c = int(75 - 25 * t)
            pygame.draw.line(floor, (c, c - 8, c - 14, 255), (0, y), (box.width, y))
        mask2 = pygame.Surface((box.width, floor_h), pygame.SRCALPHA)
        pygame.draw.rect(mask2, (255, 255, 255, 255), (0, 0, box.width, floor_h),
                         border_bottom_left_radius=14, border_bottom_right_radius=14)
        floor.blit(mask2, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        self.screen.blit(floor, (box.left, box.bottom - floor_h))

        # 3D Chrome & Gold Frame
        pygame.draw.rect(self.screen, (200, 165, 60), box.inflate(2, 2), 2, border_radius=15)
        pygame.draw.rect(self.screen, S.MARIGOLD, box, 4, border_radius=14)
        shine = pygame.Surface((box.width, 10), pygame.SRCALPHA)
        pygame.draw.rect(shine, (255, 255, 255, 40), (0, 0, box.width, 10), border_radius=14)
        self.screen.blit(shine, box.topleft)

        # Vehicle drawing on stage with 3D turntable shadow
        ground = box.bottom - 58
        top = ground - (art.rear_img[1] + art.r_rear)
        stage_shadow = pygame.Surface((int(art.width * 1.1), 16), pygame.SRCALPHA)
        pygame.draw.ellipse(stage_shadow, (0, 0, 0, 95), stage_shadow.get_rect())
        self.screen.blit(stage_shadow, stage_shadow.get_rect(center=(box.centerx, ground + 2)))
        art.draw_preview(self.screen, (box.centerx, top + art.height / 2), self.time)

        # Vehicle Info on Right
        x = 540
        ui.draw_text(self.screen, spec["name"], self.fonts.mid, S.MARIGOLD, (x, 135), "midleft", max_width=400)
        for i, line in enumerate(ui.wrap_text(self.fonts.small, spec["blurb"], 390)[:3]):
            ui.draw_text(self.screen, line, self.fonts.small, S.WHITE, (x, 172 + i * 24), "midleft", shadow=False)
        fr = vehicles.stat_fractions(spec)
        for i, (label, key) in enumerate((("SPEED", "speed"), ("ACCEL", "accel"), ("FUEL", "fuel"), ("ARMOR", "armor"))):
            self.draw_stat_bar(label, fr[key], x, 275 + i * 34)

        owned = spec["id"] in self.save["owned"]
        chosen = self.save["vehicle"] == spec["id"]
        # 3D Glass Badge
        badge_rect = pygame.Rect(x, 424, 180, 40)
        if chosen:
            ui.draw_glass_rect(self.screen, badge_rect, (10, 60, 20), alpha=200, border_color=S.LIME, border_radius=8)
            ui.draw_text(self.screen, "SELECTED", self.fonts.mid, S.LIME, badge_rect.center)
        elif owned:
            ui.draw_glass_rect(self.screen, badge_rect, (30, 40, 40), alpha=200, border_color=S.WHITE, border_radius=8)
            ui.draw_text(self.screen, "OWNED", self.fonts.mid, S.WHITE, badge_rect.center)
        else:
            ui.draw_glass_rect(self.screen, badge_rect, (60, 40, 10), alpha=200, border_color=S.MARIGOLD, border_radius=8)
            ui.draw_text(self.screen, money(spec["price"]), self.fonts.mid, S.MARIGOLD, badge_rect.center)

        text, left = self.message
        if left > 0:
            ui.draw_text(self.screen, text, self.fonts.small, S.RED, (panel.centerx, 465), max_width=800)
        label = "SELECTED" if chosen else ("SELECT" if owned else f"BUY {money(spec['price'])}")
        self.menus["garage"].set_labels(["<", label, ">", "BACK"])
        self.menus["garage"].draw(self.screen, self.fonts)

    def draw_maps(self):
        """Map screen: 3D preview card, road description, difficulty, best distance, and lock status."""
        m = maps.MAPS[self.m_idx]
        locked = not maps.is_unlocked(self.m_idx, self.save["best"])
        panel = pygame.Rect(40, 25, 920, 550)
        ui.draw_panel(self.screen, self.fonts, panel, "CHOOSE YOUR ROAD")
        
        # 3D Glass Wallet Badge in Maps
        wallet_str = money(self.save["wallet"])
        wb_w = max(145, len(wallet_str) * 14 + 50)
        wallet_rect = pygame.Rect(panel.right - wb_w - 30, panel.top + 24, wb_w, 40)
        ui.draw_glass_rect(self.screen, wallet_rect, S.PK_GREEN_DARK, alpha=200, border_color=S.MARIGOLD, border_radius=10)
        cx_coin = wallet_rect.left + 20
        cy_coin = wallet_rect.centery
        pygame.draw.circle(self.screen, (150, 95, 0), (cx_coin + 1, cy_coin + 1), 10)
        pygame.draw.circle(self.screen, S.MARIGOLD, (cx_coin, cy_coin), 9)
        pygame.draw.circle(self.screen, (255, 230, 110), (cx_coin - 2, cy_coin - 2), 3)
        ui.draw_text(self.screen, wallet_str, self.fonts.mid, S.MARIGOLD, (wallet_rect.right - 14, wallet_rect.centery), "midright")

        # 3D Map Thumbnail Card
        box = pygame.Rect(75, 125, 430, 258)
        self.screen.blit(self.map_thumb[m["id"]], box)
        if locked:
            dim = pygame.Surface(box.size, pygame.SRCALPHA)
            dim.fill((0, 0, 0, 160))
            self.screen.blit(dim, box)
            self._draw_lock(box.centerx, box.centery - 20, 52)
        pygame.draw.rect(self.screen, (200, 165, 60) if not locked else (100, 90, 80), box.inflate(2, 2), 2, border_radius=8)
        pygame.draw.rect(self.screen, S.MARIGOLD if not locked else (120, 100, 80), box, 4, border_radius=6)
        map_shine = pygame.Surface((box.width, 10), pygame.SRCALPHA)
        pygame.draw.rect(map_shine, (255, 255, 255, 40), (0, 0, box.width, 10), border_radius=6)
        self.screen.blit(map_shine, box.topleft)

        x = 540
        name_c = S.MARIGOLD if not locked else (120, 100, 80)
        ui.draw_text(self.screen, m["name"], self.fonts.mid, name_c, (x, 140), "midleft", max_width=400)
        ui.draw_text(self.screen, m["tagline"], self.fonts.small, S.LIME if not locked else (100, 100, 100),
                     (x, 176), "midleft", max_width=400)
        for i, line in enumerate(m["lines"]):
            for j, part in enumerate(ui.wrap_text(self.fonts.small, line, 390)):
                ui.draw_text(self.screen, part, self.fonts.small, S.WHITE if not locked else (100, 100, 100),
                             (x, 214 + (i * 2 + j) * 24), "midleft", shadow=False)
        ui.draw_text(self.screen, "DIFFICULTY", self.fonts.tiny, S.MARIGOLD, (x, 332), "midleft", shadow=False)
        for i in range(3):
            ui.diamond(self.screen, (x + 110 + i * 26, 332), 9, S.RED if i < m["difficulty"] else S.PK_GREEN_DARK)
        best = self.save["best"].get(m["id"], 0)
        ui.draw_text(self.screen, f"BEST: {int(best)} m", self.fonts.small, S.WHITE, (x, 366), "midleft")

        if locked:
            prev_name, req = maps.unlock_info(self.m_idx)
            prev_best = self.save["best"].get(maps.MAPS[self.m_idx - 1]["id"], 0)
            ui.draw_text(self.screen, f"LOCKED: Reach {req} m on {prev_name}",
                         self.fonts.small, S.RED, (panel.centerx, 410))
            bar_w = 300
            bx = panel.centerx - bar_w // 2
            pygame.draw.rect(self.screen, (2, 20, 10), (bx, 432, bar_w, 14), border_radius=4)
            fill = min(bar_w, int(bar_w * prev_best / req))
            if fill > 0:
                pygame.draw.rect(self.screen, S.LIME, (bx, 432, fill, 14), border_radius=4)
                pygame.draw.rect(self.screen, (210, 255, 170), (bx + 1, 433, max(1, fill - 2), 4), border_radius=2)
            pygame.draw.rect(self.screen, S.WHITE, (bx, 432, bar_w, 14), 1, border_radius=4)
            ui.draw_text(self.screen, f"{int(prev_best)} / {req} m", self.fonts.tiny, S.WHITE,
                         (panel.centerx, 439), shadow=False)
        else:
            vname = vehicles.BY_ID[self.save["vehicle"]]["name"]
            ui.draw_text(self.screen, f"DRIVING: {vname}", self.fonts.small, S.MARIGOLD,
                         (panel.centerx, 440), max_width=800)

        text, left = self.message
        if left > 0:
            ui.draw_text(self.screen, text, self.fonts.small, S.RED, (panel.centerx, 465), max_width=800)
        btn_label = "LOCKED" if locked else "DRIVE!"
        self.menus["maps"].set_labels(["<", btn_label, ">", "BACK"])
        self.menus["maps"].draw(self.screen, self.fonts)

    def _draw_lock(self, cx, cy, sz):
        """Draw an illuminated 3D metallic padlock icon."""
        target = self.screen
        body_w, body_h = int(sz * 0.65), int(sz * 0.48)
        bx = cx - body_w // 2
        by = cy + int(sz * 0.05)
        pygame.draw.rect(target, (0, 0, 0, 100), (bx + 3, by + 3, body_w, body_h), border_radius=6)
        pygame.draw.rect(target, (195, 160, 50), (bx, by, body_w, body_h), border_radius=6)
        pygame.draw.rect(target, (255, 225, 110), (bx + 2, by + 2, body_w - 4, body_h // 3), border_radius=4)
        pygame.draw.rect(target, (240, 205, 70), (bx, by, body_w, body_h), 2, border_radius=6)
        shackle_r = int(sz * 0.24)
        pygame.draw.arc(target, (180, 180, 185), (cx - shackle_r, by - shackle_r * 2 + 3,
                        shackle_r * 2, shackle_r * 2), 0, math.pi, max(3, sz // 11))
        pygame.draw.arc(target, (255, 255, 255), (cx - shackle_r + 1, by - shackle_r * 2 + 2,
                        shackle_r * 2 - 2, shackle_r * 2 - 2), 0, math.pi, 2)
        kh = max(2, sz // 9)
        pygame.draw.circle(target, (50, 40, 15), (cx, by + body_h // 2 - 2), kh + 1)
        pygame.draw.rect(target, (50, 40, 15), (cx - 1, by + body_h // 2, 3, kh + 3))

    # ---- shop ----
    def shop_upgrade(self):
        """Buy the next upgrade level for the currently browsed powerup."""
        spec = powerups.POWERUPS[self.s_idx]
        pid = spec["id"]
        levels = self.save.setdefault("powerup_levels", {})
        current = levels.get(pid, 0)
        if current >= 2:
            self.message = ("Already at max level!", 2.0)
            sound.play("error")
            return
        cost = powerups.UPGRADE_COSTS[current + 1]
        if self.save["wallet"] < cost:
            self.message = (f"Need {money(cost - self.save['wallet'])} more!", 2.5)
            sound.play("error")
            return
        self.save["wallet"] -= cost
        levels[pid] = current + 1
        self.persist()
        sound.play("buy")
        self.message = (f"Upgraded to Level {current + 2}!", 2.0)

    def draw_shop(self):
        """Shop screen: 3D showcase card, pulsing icon aura, gem tier indicators, and upgrades."""
        spec = powerups.POWERUPS[self.s_idx]
        pid = spec["id"]
        levels = self.save.get("powerup_levels", {})
        lvl = levels.get(pid, 0)
        stats = powerups.UPGRADES[pid][lvl]

        panel = pygame.Rect(40, 25, 920, 550)
        ui.draw_panel(self.screen, self.fonts, panel, "POWER SHOP")
        
        # 3D Glass Wallet Badge in Shop
        wallet_str = money(self.save["wallet"])
        wb_w = max(145, len(wallet_str) * 14 + 50)
        wallet_rect = pygame.Rect(panel.right - wb_w - 30, panel.top + 24, wb_w, 40)
        ui.draw_glass_rect(self.screen, wallet_rect, S.PK_GREEN_DARK, alpha=200, border_color=S.MARIGOLD, border_radius=10)
        cx_coin = wallet_rect.left + 20
        cy_coin = wallet_rect.centery
        pygame.draw.circle(self.screen, (150, 95, 0), (cx_coin + 1, cy_coin + 1), 10)
        pygame.draw.circle(self.screen, S.MARIGOLD, (cx_coin, cy_coin), 9)
        pygame.draw.circle(self.screen, (255, 230, 110), (cx_coin - 2, cy_coin - 2), 3)
        ui.draw_text(self.screen, wallet_str, self.fonts.mid, S.MARIGOLD, (wallet_rect.right - 14, wallet_rect.centery), "midright")

        # 3D Powerup Pedestal Box
        box = pygame.Rect(75, 115, 430, 300)
        pygame.draw.rect(self.screen, (20, 38, 32), box, border_radius=14)
        aura = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
        pulse = 0.5 + 0.5 * math.sin(self.time * 3)
        pygame.draw.circle(aura, (*spec["color"], int(25 + 20 * pulse)), (box.width // 2, box.height // 2 - 10), 120)
        self.screen.blit(aura, box.topleft)

        pygame.draw.rect(self.screen, (150, 150, 150), box.inflate(2, 2), 2, border_radius=15)
        pygame.draw.rect(self.screen, spec["color"], box, 4, border_radius=14)
        powerups.draw_icon_large(self.screen, box.centerx, box.centery - 10, pid, self.time)

        # Info on the right with glass cards
        x = 540
        ui.draw_text(self.screen, spec["name"], self.fonts.big, spec["color"], (x, 130), "midleft")
        for i in range(3):
            c = S.MARIGOLD if i <= lvl else (40, 60, 50)
            ui.diamond(self.screen, (x + i * 28, 175), 10, c)
        ui.draw_text(self.screen, f"LEVEL {lvl + 1}", self.fonts.small, S.WHITE, (x + 98, 175), "midleft")
        
        curr_card = pygame.Rect(x - 10, 200, 370, 42)
        ui.draw_glass_rect(self.screen, curr_card, (20, 45, 35), alpha=180, border_color=(60, 120, 80), border_radius=8)
        ui.draw_text(self.screen, stats["desc"], self.fonts.small, S.LIME, curr_card.center)

        if lvl < 2:
            nxt = powerups.UPGRADES[pid][lvl + 1]
            cost = powerups.UPGRADE_COSTS[lvl + 1]
            ui.draw_text(self.screen, "NEXT LEVEL:", self.fonts.tiny, S.MARIGOLD, (x, 262), "midleft", shadow=False)
            nxt_card = pygame.Rect(x - 10, 280, 370, 42)
            ui.draw_glass_rect(self.screen, nxt_card, (35, 30, 20), alpha=180, border_color=S.MARIGOLD, border_radius=8)
            ui.draw_text(self.screen, nxt["desc"], self.fonts.small, S.WHITE, nxt_card.center)
            ui.draw_text(self.screen, f"Cost: {money(cost)}", self.fonts.mid, S.MARIGOLD, (x, 345), "midleft")
        else:
            ui.draw_text(self.screen, "MAX LEVEL REACHED", self.fonts.mid, S.LIME, (x, 280), "midleft")

        text, left = self.message
        if left > 0:
            ui.draw_text(self.screen, text, self.fonts.small, S.RED, (panel.centerx, 450), max_width=800)

        label = "MAX LEVEL" if lvl >= 2 else f"UPGRADE {money(powerups.UPGRADE_COSTS[lvl + 1])}"
        self.menus["shop"].set_labels(["<", label, ">", "BACK"])
        self.menus["shop"].draw(self.screen, self.fonts)

    # ---- sound ----
    def engine_volume(self):
        """How loud the engine loop should be (0 = silent). Only sounds while actually driving with fuel."""
        r = self.rickshaw
        if self.state != "playing" or r is None or r.fuel <= 0:
            return 0.0
        return 0.3 + 0.5 * min(1.0, abs(r.speed) / r.spec["max_speed"]) + (0.2 if r.throttle else 0.0)

    # ---- main loop ----
    def run(self):
        """Main loop: events -> fixed-step physics (120 Hz) -> draw, until the player quits."""
        accumulator = 0.0
        while self.running:
            frame_time = min(self.clock.tick(S.FPS) / 1000, 0.1)
            self.time += frame_time
            self.message = (self.message[0], max(0.0, self.message[1] - frame_time))
            self.handle_events()
            sound.engine(self.engine_volume())
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