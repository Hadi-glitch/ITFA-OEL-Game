# vehicle.py - one drivable vehicle: physics from its spec + animation (spinning wheels, suspension, tilt) + drawing.
import math
import random
import pygame
import settings as S
import terrain
import sound
import powerups

DUST = (175, 150, 115)


def make_glow(r=30):
    """Soft yellow headlight glow built from concentric translucent circles."""
    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r, 0, -2):
        pygame.draw.circle(s, (255, 230, 150, int(110 * (1 - i / r) ** 2)), (r, r), i)
    return s


def make_shadow():
    """Flat dark ellipse placed under the vehicle on the road."""
    s = pygame.Surface((160, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, 90), s.get_rect())
    return s


class Rickshaw:
    """Driving physics, fuel, health and all animation state for the currently chosen vehicle."""

    def __init__(self, art):
        """`art` is a vehicles.VehicleArt (sprites + measurements); its .spec holds the stats."""
        self.art = art
        self.spec = art.spec
        self.glow = make_glow()
        self.shadow = make_shadow()
        # Measurements from the artwork (pixels, relative to the pivot between the two hubs)
        self.dxr = art.rear_img[0] - art.pivot[0]       # rear hub is this far behind the pivot (negative)
        self.dxf = art.front_img[0] - art.pivot[0]      # front hub is this far ahead
        self.dyr = art.rear_img[1] - art.pivot[1]
        self.dyf = art.front_img[1] - art.pivot[1]
        self.r_rear, self.r_front = art.r_rear, art.r_front
        self.front_ext = art.width - art.pivot[0]       # nose of the vehicle, used for crashes
        self.rear_ext = art.pivot[0]
        self.height = art.height
        self.fuel_max = self.spec["fuel"]
        self.mass = self.spec["mass"]
        self.powerups = powerups.ActivePowerups()
        self.reset()

    def reset(self):
        """Put the vehicle at the start line with a full tank, full health and calm animation."""
        self.x = S.START_X
        self.speed = 0.0                  # horizontal speed, px/s
        self.y = terrain.get_height(self.x)
        self.vy = 0.0                     # vertical speed (positive = falling)
        self.on_ground = True
        self.fuel = self.fuel_max
        self.health = self.spec["armor"]
        self.coins = 0
        self.powerups.clear()
        self.pending_flash = None
        self.accel = 0.0                  # m/s^2
        self.slope_deg = 0.0
        self.throttle = False
        self.braking = False
        self.hit_cooldown = 0.0
        self.impact = 0.0                 # set by crashes/landings; the game turns it into screen shake
        # animation state
        self.wheel_angle = 0.0
        self.wheel_omega = 0.0
        self.angle = self.ground_angle()
        self.pitch = 0.0
        self.pitch_vel = 0.0
        self.susp = 0.0
        self.susp_vel = 0.0
        self.hub_off = [0.0, 0.0]
        self.rear_hub = (0.0, 0.0)
        self.front_hub = (0.0, 0.0)
        self.prev_ground = terrain.get_height(self.x)
        self.prev_ground_vy = 0.0
        self.smoke_timer = 0.0
        self.dust_timer = 0.0
        self.update_pose(0.0)

    @property
    def air_height(self):
        """Height of the wheels above the road, in metres."""
        return max(0.0, (terrain.get_height(self.x) - self.y) / S.PIXELS_PER_METER)

    def ground_angle(self):
        """Body tilt (radians) that makes both wheels sit on the road at the current x."""
        rx, fx = self.x + self.dxr, self.x + self.dxf
        ry, fy = terrain.get_height(rx) - self.r_rear, terrain.get_height(fx) - self.r_front
        return math.atan2(fy - ry, fx - rx) - self.art.tilt0

    def jump(self):
        """Called once per key press. Only works while on the ground."""
        if self.on_ground:
            self.vy = -S.JUMP_SPEED       # negative y is upward
            self.on_ground = False
            if self.speed < 140:          # a small forward hop so you can leap a rock from a standstill
                self.speed = 140.0

    def activate_powerup(self, powerup_id):
        """Start a powerup effect. Called when the player collects a powerup pickup."""
        self.powerups.activate(powerup_id)
        self.pending_flash = (powerups.BY_ID[powerup_id]["color"], 60)

    # ---------------- physics ----------------
    def update(self, dt, keys, fx):
        """One fixed physics step: forces -> speed -> position, then animation and particles."""
        sp = self.spec
        self.throttle = bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])
        self.braking = bool(keys[pygame.K_LEFT] or keys[pygame.K_a])

        # Horizontal: force -> acceleration (a = F/m) -> speed
        v = self.speed / S.PIXELS_PER_METER          # m/s
        force, burning = 0.0, False
        if self.on_ground:                           # wheels need traction
            if self.throttle and self.fuel > 0:
                force += sp["drive"]
                burning = True
            if self.braking:
                if v > 0.1:
                    force -= sp["brake"]
                elif self.fuel > 0:                  # reverse
                    force -= sp["drive"] * 0.5
                    burning = True
        if burning:
            self.fuel = max(0.0, self.fuel - S.FUEL_DRAIN * dt)
        force -= S.DRAG * v
        self.accel = force / self.mass
        v += self.accel * dt
        max_spd = sp["max_speed"]
        if self.powerups.active("speed_boost"):
            max_spd *= self.powerups.stats("speed_boost")["mult"]
        self.speed = max(-S.MAX_REVERSE, min(max_spd, v * S.PIXELS_PER_METER))
        self.x += self.speed * dt
        self.slope_deg = math.degrees(terrain.get_angle(self.x))

        # Vertical: gravity -> vertical speed -> height
        landed_vy = 0.0
        ground_y = terrain.get_height(self.x)
        if self.on_ground:
            self.y = ground_y
        else:
            self.vy += S.GRAVITY * dt
            self.y += self.vy * dt
            if self.y >= ground_y:
                landed_vy = self.vy
                self.y, self.vy, self.on_ground = ground_y, 0.0, True

        if landed_vy > 0:
            self.on_land(landed_vy, fx)
        # Powerup timers and effects
        self.powerups.update(dt)
        if self.powerups.active("health_regen"):
            s = self.powerups.stats("health_regen")
            self.health = min(self.spec["armor"], self.health + s["total"] / s["duration"] * dt)

        self.update_pose(dt)
        self.animate(dt, fx)

    def on_land(self, vy, fx):
        """Landing reaction: sound, suspension kick, shake strength, wheel smoothing and a dust burst."""
        sound.play("land", max(0.3, min(1.0, vy / S.JUMP_SPEED)))
        self.susp_vel += vy * 0.25
        self.impact = max(self.impact, min(vy / S.JUMP_SPEED, 1.2) * 7)
        for i, (wx, hub, r) in enumerate(((self.x + self.dxr, self.rear_hub, self.r_rear),
                                          (self.x + self.dxf, self.front_hub, self.r_front))):
            off = hub[1] - (terrain.get_height(wx) - r)             # how far the wheel was from the road
            self.hub_off[i] = max(-14.0, min(14.0, off))
            for _ in range(8):
                fx.emit(wx, terrain.get_height(wx), random.uniform(-120, 120) + self.speed * 0.3,
                        -random.uniform(20, 110), 0.6, 3, 10, DUST, 150, 200)

    # ---------------- pose + animation ----------------
    def update_pose(self, dt):
        """Work out where both wheel hubs are and how the body is tilted (road-following or airborne)."""
        if self.on_ground:
            rx, fx_ = self.x + self.dxr, self.x + self.dxf
            self.angle += (self.ground_angle() - self.angle) * min(1.0, 16 * dt)   # settle onto the slope
            decay = math.exp(-20 * dt)                                              # post-landing offset fades
            self.hub_off = [o * decay for o in self.hub_off]
            self.rear_hub = (rx, terrain.get_height(rx) - self.r_rear + self.hub_off[0])
            self.front_hub = (fx_, terrain.get_height(fx_) - self.r_front + self.hub_off[1])
        else:
            target = max(-0.5, min(0.5, self.vy / 1500))                            # nose up rising, nose down falling
            self.angle += (target - self.angle) * min(1.0, 3 * dt)
            px, py = self.x, self.y - (self.r_rear + self.r_front) / 2
            c, s = math.cos(self.angle), math.sin(self.angle)
            self.rear_hub = (px + self.dxr * c - self.dyr * s, py + self.dxr * s + self.dyr * c)
            self.front_hub = (px + self.dxf * c - self.dyf * s, py + self.dxf * s + self.dyf * c)

    def animate(self, dt, fx):
        """Spin wheels, bounce suspension, tilt the body and emit smoke/dust."""
        v = self.speed / S.PIXELS_PER_METER
        has_fuel = self.fuel > 0

        # Wheels: rolling without slipping means omega = speed / radius
        if self.on_ground:
            omega = self.speed / self.r_rear
            if self.throttle and has_fuel and abs(v) < 4.0:
                omega += 18.0 * (1 - abs(v) / 4.0)                     # wheelspin when launching
            self.wheel_omega += (omega - self.wheel_omega) * min(1.0, 25 * dt)
        elif self.throttle and has_fuel:
            self.wheel_omega = min(30.0, self.wheel_omega + 40 * dt)   # engine revs in the air
        else:
            self.wheel_omega *= max(0.0, 1 - 0.4 * dt)                 # wheels slowly wind down
        self.wheel_angle = (self.wheel_angle + self.wheel_omega * dt) % math.tau

        # Body pitch: spring toward a tilt proportional to acceleration (squat on gas, dive on brake)
        target_pitch = -self.accel * S.PITCH_GAIN if self.on_ground else 0.0
        self.pitch_vel += (120.0 * (target_pitch - self.pitch) - 10.0 * self.pitch_vel) * dt
        self.pitch += self.pitch_vel * dt

        # Suspension: spring-damper (F = -kx - cv); road bumps give it a kick
        ground = terrain.get_height(self.x)
        ground_vy = (ground - self.prev_ground) / dt if dt > 0 else 0.0
        if self.on_ground:
            self.susp_vel -= (ground_vy - self.prev_ground_vy) * 0.4
        self.prev_ground, self.prev_ground_vy = ground, ground_vy
        k, c = self.spec["susp_k"], self.spec["susp_c"]
        self.susp_vel += (-k * self.susp - c * self.susp_vel) * dt
        self.susp = max(-S.SUSP_MAX, min(S.SUSP_MAX, self.susp + self.susp_vel * dt))

        # Exhaust smoke while the engine is running
        self.smoke_timer -= dt
        if self.throttle and has_fuel and self.smoke_timer <= 0:
            self.smoke_timer = 0.04 if self.accel > 3 else 0.1
            ex, ey = self.to_world(*self.art.exhaust)
            fx.emit(ex, ey, self.speed * 0.3 - 60, -25 - random.random() * 20, 0.9, 3, 11, (85, 85, 85), 150, -15)

        # Dust kicked up by the rear wheel (more when launching or skidding)
        slipping = self.throttle and has_fuel and abs(v) < 4.0
        skidding = self.braking and v > 6.0
        self.dust_timer -= dt
        if self.on_ground and self.dust_timer <= 0 and (abs(self.speed) > 60 or slipping or skidding):
            hard = slipping or skidding
            self.dust_timer = 0.03 if hard else 0.06
            hx, hy = self.rear_hub
            fx.emit(hx, hy + self.r_rear, -self.speed * 0.25 - (50 if slipping else 0) + random.uniform(-20, 20),
                    -random.uniform(15, 70 if hard else 30), 0.55, 2, 8, terrain.current()["dust"], 140, 120)

    # ---------------- drawing ----------------
    def to_world(self, lx, ly):
        """Convert a point on the body picture to world pixels, including tilt and suspension travel."""
        px = (self.rear_hub[0] + self.front_hub[0]) / 2
        py = (self.rear_hub[1] + self.front_hub[1]) / 2
        a = self.angle + self.pitch
        dx, dy = lx - self.art.pivot[0], ly - self.art.pivot[1] + self.susp
        c, s = math.cos(a), math.sin(a)
        return px + dx * c - dy * s, py + dx * s + dy * c

    def draw(self, screen, camera_x):
        """Draw shadow, spinning wheels, tilted body and headlight glow."""
        ox = -camera_x
        ground = terrain.get_height(self.x)

        # Shadow shrinks as the vehicle leaves the ground
        h = max(0.0, ground - self.y)
        if h < 200:
            w = int(self.art.width * max(0.4, 1 - h / 200))
            sh = pygame.transform.smoothscale(self.shadow, (w, 14)) if h > 2 else pygame.transform.smoothscale(self.shadow, (self.art.width, 14))
            screen.blit(sh, sh.get_rect(center=(self.x + ox, ground + 3)))

        # Wheels first (the body's fenders then cover their tops)
        for hub, img in ((self.rear_hub, self.art.wheel_r), (self.front_hub, self.art.wheel_f)):
            rot = pygame.transform.rotate(img, -math.degrees(self.wheel_angle))
            screen.blit(rot, rot.get_rect(center=(hub[0] + ox, hub[1])))

        # Body: rotate the picture around its centre, then place that centre in the world
        a = self.angle + self.pitch
        rotated = pygame.transform.rotate(self.art.body, -math.degrees(a))   # pygame rotates counter-clockwise
        cx, cy = self.to_world(self.art.width / 2, self.art.height / 2)
        screen.blit(rotated, rotated.get_rect(center=(cx + ox, cy)))

        if self.art.head:                                                    # headlight glow
            gx, gy = self.to_world(*self.art.head)
            screen.blit(self.glow, self.glow.get_rect(center=(gx + ox, gy)))