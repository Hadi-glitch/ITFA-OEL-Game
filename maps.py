# maps.py - the three Karachi maps: road shape, colours, scenery and hazards, plus their skyline pictures.
import math
import random
import pygame
import settings as S
import assets

# terrain = list of (amplitude px, period px) sine waves added together; rough = tiny fast bumps (px).
# hazards = weights for what appears in a 320 px cell of road; density = chance a cell holds something.
MAPS = [
    dict(id="university", name="UNIVERSITY ROAD", seed=11,
         tagline="Red Line construction zone",
         lines=["Dug-up lanes, dust and metro pillars.", "Barrels, barricades, rubble and deep potholes."],
         difficulty=2, density=0.62, rough=2.5, unlock_req=0,
         terrain=[(38, 150), (24, 55)],
         hazards=[("pothole", 3), ("rock", 3), ("barrel", 3), ("barricade", 2), ("bump", 2), ("cone", 2)],
         scenery=["pillar", "crane", "pole", "tree", "billboard", "stall", "none"],
         sky=((236, 190, 130), (250, 226, 180)), skyline="university",
         road=(98, 84, 68), road_top=(168, 140, 96), asphalt=(70, 62, 56), dust=(190, 160, 120),
         billboards=["BIRYANI", "MOBILE LOAD", "SALE 50%", "ADMISSIONS"]),
    dict(id="lyari", name="LYARI KI GALIYAN", seed=23,
         tagline="Narrow lanes, broken roads",
         lines=["Rough cobbles, sewage puddles, handcarts.", "Rubbish heaps and endless bumps."],
         difficulty=3, density=0.72, rough=5.0, unlock_req=500,
         terrain=[(24, 120), (14, 46), (6, 17)],
         hazards=[("pothole", 4), ("garbage", 3), ("cart", 2), ("rock", 2), ("bump", 3), ("cone", 1)],
         scenery=["laundry", "pole", "stall", "tree", "laundry", "none"],
         sky=((205, 160, 120), (238, 205, 160)), skyline="lyari",
         road=(86, 72, 62), road_top=(130, 108, 84), asphalt=(60, 54, 50), dust=(165, 140, 110),
         billboards=["CHAI", "PAN", "FRESH JUICE"]),
    dict(id="faisal", name="SHAHRAH-E-FAISAL", seed=37,
         tagline="Rush-hour on the main artery",
         lines=["Smoother asphalt but heavy traffic.", "Broken-down cars, speed breakers, cones."],
         difficulty=2, density=0.58, rough=1.2, unlock_req=800,
         terrain=[(48, 260), (14, 70)],
         hazards=[("car", 4), ("bump", 3), ("cone", 3), ("barricade", 2), ("pothole", 2), ("rock", 1)],
         scenery=["billboard", "bridge", "pole", "tree", "billboard", "none"],
         sky=((150, 190, 230), (235, 232, 215)), skyline="faisal",
         road=(78, 78, 82), road_top=(150, 150, 150), asphalt=(52, 52, 56), dust=(170, 170, 170),
         billboards=["SALE", "MOBILE", "CAR LOAN", "PIZZA", "BANK"]),
]
BY_ID = {m["id"]: m for m in MAPS}


def is_unlocked(idx, best_dict):
    """True if the map at index `idx` is playable. Map 0 always is; later maps
    need the player to reach unlock_req metres on the PREVIOUS map."""
    m = MAPS[idx]
    if m["unlock_req"] == 0:
        return True
    prev = MAPS[idx - 1]
    return best_dict.get(prev["id"], 0) >= m["unlock_req"]


def unlock_info(idx):
    """Return (prev_map_name, required_distance) for a locked map."""
    m = MAPS[idx]
    prev = MAPS[idx - 1]
    return prev["name"], m["unlock_req"]


def build_background(m):
    art = assets.load_image("backgrounds", f"{m['id']}.png", alpha=False, height=S.HEIGHT)
    if art is not None and art.get_width() >= S.WIDTH:
        return art                      # painted skyline: already loops, no mirroring needed
    # Draw a seamless-looking skyline picture (2 screens wide); it is tiled with parallax.
    w = S.WIDTH * 2
    surf = pygame.Surface((w, S.HEIGHT))
    top, bottom = m["sky"]
    for y in range(S.HEIGHT):                                    # sky gradient
        t = y / S.HEIGHT
        pygame.draw.line(surf, tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)), (0, y), (w, y))
    pygame.draw.circle(surf, (255, 246, 215), (w // 4, 120), 52)  # hazy sun
    rng = random.Random(m["seed"])
    base = S.HEIGHT - 150
    kind = m["skyline"]
    x = 0
    while x < w:
        if kind == "university":                                 # low blocks, domes, a few cranes
            bw, bh = rng.randint(50, 110), rng.randint(60, 190)
            sh = rng.randint(150, 185)
            pygame.draw.rect(surf, (sh, sh - 25, sh - 45), (x, base - bh, bw, bh + 150))
            if rng.random() < 0.3:
                pygame.draw.circle(surf, (sh - 20, sh - 45, sh - 65), (x + bw // 2, base - bh), bw // 3)
            if rng.random() < 0.12:
                pygame.draw.line(surf, (200, 160, 40), (x + 10, base - bh), (x + 10, base - bh - 90), 4)
                pygame.draw.line(surf, (200, 160, 40), (x + 10, base - bh - 90), (x + 80, base - bh - 80), 3)
        elif kind == "lyari":                                    # tightly packed low houses with flat roofs
            bw, bh = rng.randint(40, 75), rng.randint(70, 160)
            c = rng.choice([(176, 120, 90), (196, 150, 100), (150, 120, 105), (205, 175, 120), (130, 150, 150)])
            pygame.draw.rect(surf, c, (x, base - bh, bw, bh + 150))
            for wy in range(base - bh + 12, base - 10, 26):      # windows
                for wx in range(x + 8, x + bw - 12, 18):
                    pygame.draw.rect(surf, (60, 45, 40), (wx, wy, 8, 12))
            pygame.draw.rect(surf, (c[0] - 30, c[1] - 30, c[2] - 30), (x, base - bh, bw, 5))
        else:                                                    # tall glassy towers
            bw, bh = rng.randint(55, 100), rng.randint(110, 330)
            sh = rng.randint(110, 150)
            pygame.draw.rect(surf, (sh - 20, sh, sh + 40), (x, base - bh, bw, bh + 150))
            for wy in range(base - bh + 10, base, 18):
                pygame.draw.line(surf, (sh + 40, sh + 70, sh + 100), (x + 4, wy), (x + bw - 4, wy), 2)
            if rng.random() < 0.2:
                pygame.draw.line(surf, (90, 90, 100), (x + bw // 2, base - bh), (x + bw // 2, base - bh - 40), 3)
        x += bw + rng.randint(0, 10)
    haze = pygame.Surface((w, S.HEIGHT), pygame.SRCALPHA)         # warm haze so the skyline sits far away
    haze.fill((*bottom, 60))
    surf.blit(haze, (0, 0))
    mirrored = pygame.Surface((w * 2, S.HEIGHT))                  # mirror so the tile has no visible seam
    mirrored.blit(surf, (0, 0))
    mirrored.blit(pygame.transform.flip(surf, True, False), (w, 0))
    return mirrored
