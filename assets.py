# assets.py - one safe, cached place to load PNG artwork. A missing/broken file returns None,
# so the caller simply keeps its procedural (shape-drawn) fallback.
import os
import pygame
import settings as S

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")
_cache = {}          # key -> Surface or None (None is cached too, so a missing file is only looked for once)


def path(*parts):
    """Return the full path of a file inside the assets folder, e.g. path('backgrounds', 'university.png')."""
    return os.path.join(ASSET_DIR, *parts)


def exists(*parts):
    """True if the asset file is present on disk (does not load it)."""
    return os.path.isfile(path(*parts))


def load_image(*parts, alpha=True, size=None, height=None):
    """Load assets/<parts> once and cache it.

    alpha  - keep transparency (use False for opaque backgrounds, it draws faster)
    size   - optional (w, h) to scale to
    height - optional height to scale to, keeping the picture's proportions
    Returns a Surface, or None if the file is missing or cannot be read."""
    key = (parts, alpha, size, height)
    if key in _cache:
        return _cache[key]
    img = None
    file = path(*parts)
    try:
        img = pygame.image.load(file)
        img = img.convert_alpha() if alpha else img.convert()
        if height is not None:
            size = (max(1, round(img.get_width() * height / img.get_height())), height)
        if size is not None:
            img = pygame.transform.smoothscale(img, size)
        if S.ASSET_DEBUG:
            print(f"[assets] loaded  {'/'.join(parts)}  {img.get_width()}x{img.get_height()}")
    except (pygame.error, FileNotFoundError, OSError):
        img = None
        if S.ASSET_DEBUG:
            print(f"[assets] missing {'/'.join(parts)}  (using the built-in drawing)")
    _cache[key] = img
    return img
