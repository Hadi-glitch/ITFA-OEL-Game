# terrain.py - road shape, potholes, speed breakers and where obstacles/pickups sit. Depends on the selected map.
import math
import random
from functools import lru_cache
import settings as S
import maps

CELL = 420                 # the road is generated in 420 px chunks, each seeded so a map is always the same
_cur = maps.MAPS[0]        # the map currently being played


def set_map(m):
    """Choose which map (a dict from maps.py) all later height/content queries use."""
    global _cur
    _cur = m


def current():
    """Return the map dict currently in use."""
    return _cur


def _pick(rng, table):
    """Pick one name from a list of (name, weight) pairs."""
    total = sum(w for _, w in table)
    r = rng.uniform(0, total)
    for name, w in table:
        r -= w
        if r <= 0:
            return name
    return table[-1][0]


def _base(m, x):
    """Road height from the smooth hills and cobbles only (no potholes/bumps), used to find flat spots."""
    y = S.HEIGHT - 150
    for amp, period in m["terrain"]:
        y += amp * math.sin(x / period)
    return y + m["rough"] * math.sin(x / 9.5 + math.sin(x / 37.0))


@lru_cache(maxsize=2048)
def _cell(map_id, cell):
    """Generate (once) what lives in one road cell: terrain features, solid obstacles and pickups."""
    m = maps.BY_ID[map_id]
    rng = random.Random(m["seed"] * 100003 + cell)
    x0 = cell * CELL
    terr, obs, pick = [], [], []
    safe = cell < 2                                   # keep the start line clear
    density = min(0.92, m["density"] + 0.006 * max(0, cell - 2))   # busier the further you drive

    def add(kind, cx):
        """Create one hazard of `kind` centred at world x `cx`."""
        if kind == "pothole":
            terr.append(dict(kind=kind, c=cx, hw=rng.uniform(36, 56), amount=rng.uniform(14, 26)))
        elif kind == "bump":
            terr.append(dict(kind=kind, c=cx, hw=rng.uniform(28, 38), amount=rng.uniform(9, 15)))
        else:
            size = {"rock": (rng.randint(32, 58), rng.randint(24, 42)), "barrel": (28, 40), "cone": (18, 26),
                    "barricade": (76, 38), "garbage": (rng.randint(60, 84), rng.randint(24, 34)),
                    "cart": (84, 48), "car": (112, 52)}[kind]
            obs.append(dict(kind=kind, x0=cx - size[0] / 2, w=size[0], h=size[1], variant=rng.randint(0, 3)))

    if not safe and rng.random() < density:
        kind = _pick(rng, m["hazards"])
        cx, best = None, 1e9
        for _ in range(16):                          # prefer a flat stretch that is not at the top of a steep climb
            cand = x0 + rng.uniform(110, CELL - 110)  # kept away from cell edges so neighbours are >= 200 px apart
            slope = abs(_base(m, cand + 60) - _base(m, cand - 60)) / 120
            climb = _base(m, cand - 220) - _base(m, cand + 30)     # how much higher the spot is than the road before it
            score = max(slope * 150, climb)
            if score < best:
                cx, best = cand, score
            if slope < 0.12 and climb < 16:
                break
        if best > 20 and kind not in ("pothole", "bump"):
            kind = "pothole"                          # no fair flat spot here: use a pothole instead of a wall
        add(kind, cx)
        if kind in ("cone", "barrel") and rng.random() < 0.35:         # a second item nearby
            cx2 = cx + rng.choice((-1, 1)) * rng.uniform(120, 150)
            if x0 + 40 < cx2 < x0 + CELL - 40:
                add(kind, cx2)

    solid = [o for o in obs if o["kind"] in ("rock", "cart", "car", "barricade", "garbage")]
    if rng.random() < 0.6:                                                     # coins
        if solid and rng.random() < 0.7:                                       # an arc over an obstacle: jump to collect
            o = solid[0]
            mid = o["x0"] + o["w"] / 2
            for i in range(-3, 4):
                up = o["h"] + 32 + 46 * (1 - (i / 3) ** 2)
                pick.append(dict(kind="coin", x=mid + i * 30, up=up))
        else:                                                                  # a straight line at driving height
            sx = x0 + rng.uniform(30, 120)
            for i in range(5):
                pick.append(dict(kind="coin", x=sx + i * 36, up=38))
    if not safe and rng.random() < 0.09:                                       # CNG cylinder
        pick.append(dict(kind="cng", x=x0 + rng.uniform(60, CELL - 60), up=36))
    return dict(terr=terr, obs=obs, pick=pick)


def cell_content(cell):
    """Return the generated content dict of a cell for the current map."""
    return _cell(_cur["id"], cell)


def get_height(x):
    """Return the road's y position (pixels, screen y points down) at world x."""
    m = _cur
    y = _base(m, x)
    for f in _cell(m["id"], math.floor(x / CELL))["terr"]:
        d = abs(x - f["c"])
        if d < f["hw"]:
            t = d / f["hw"]
            if f["kind"] == "pothole":
                y += f["amount"] * (1 - t ** 3)                    # dip down (screen y grows downward)
            else:
                y -= f["amount"] * (0.5 + 0.5 * math.cos(math.pi * t))   # speed breaker hump
    return y


def get_angle(x, span=4):
    """Return the road angle in radians at world x (positive = uphill), found by sampling two nearby points."""
    dy = get_height(x + span) - get_height(x - span)
    return math.atan2(-dy, 2 * span)


def features_in(x_from, x_to):
    """List the potholes/speed breakers whose cells overlap [x_from, x_to] (used to paint them)."""
    out = []
    for cell in range(math.floor(x_from / CELL), math.floor(x_to / CELL) + 1):
        out.extend(_cell(_cur["id"], cell)["terr"])
    return out
