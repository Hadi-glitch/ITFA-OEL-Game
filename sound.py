# sound.py - one safe, cached place to play sound effects. A missing file or no audio device means silence, never a crash.
import os
import pygame
import settings as S

pygame.mixer.pre_init(44100, -16, 2, 512)    # small buffer = low delay; must run before pygame.init()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")
_ok = False
_cache = {}          # name -> Sound or None (None is cached too, so a missing file is only looked for once)
_engine = None       # reserved mixer channel 0: used only by the looping engine sound

# Windows' default audio driver (WASAPI) sometimes refuses to start; the older drivers nearly always work.
DRIVERS = (None, "directsound", "winmm") if os.name == "nt" else (None,)


def _open_mixer():
    """Open the audio device, trying each driver and a couple of buffer sizes. Raises pygame.error if all fail."""
    last = None
    for driver in DRIVERS:
        if driver:
            os.environ["SDL_AUDIODRIVER"] = driver
        for buf in (512, 2048):
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=buf)
                if S.ASSET_DEBUG:
                    print(f"[sound] audio ready (driver: {driver or 'default'}, buffer {buf})")
                return
            except pygame.error as e:
                last = e
    raise last


def init():
    """Start the mixer (call once, after pygame.init()). With no audio device everything stays silent."""
    global _ok, _engine
    try:
        if not pygame.mixer.get_init():              # pygame.init() could not open it: retry with other drivers
            _open_mixer()
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(1)                 # channel 0 is kept free for the engine loop
        _engine = pygame.mixer.Channel(0)
        _ok = True
    except pygame.error as e:
        _ok = False
        if S.ASSET_DEBUG:
            print(f"[sound] no audio device - running silent ({e})")


def _load(name):
    """Load assets/sounds/<name>.wav (or .ogg) once and cache it; None if missing or unreadable."""
    if name in _cache:
        return _cache[name]
    snd = None
    for ext in (".wav", ".ogg"):
        file = os.path.join(SOUND_DIR, name + ext)
        if os.path.isfile(file):
            try:
                snd = pygame.mixer.Sound(file)
                break
            except pygame.error:
                snd = None
    if S.ASSET_DEBUG:
        print(f"[sound] {'loaded ' if snd else 'missing'} {name}")
    _cache[name] = snd
    return snd


def play(name, volume=1.0):
    """Play a short effect once. Does nothing if sound is off, the mixer failed or the file is missing."""
    if not _ok or not S.SOUND_ON:
        return
    snd = _load(name)
    if snd is not None:
        snd.set_volume(volume * S.SFX_VOLUME)
        snd.play()


def engine(volume):
    """Keep the looping engine sound running at `volume` (0..1); 0 stops it. Call once per frame."""
    if not _ok or _engine is None:
        return
    if not S.SOUND_ON or volume <= 0.01:
        _engine.stop()
        return
    snd = _load("engine_loop")
    if snd is None:
        return
    if not _engine.get_busy():
        _engine.play(snd, loops=-1)
    _engine.set_volume(min(1.0, volume * S.SFX_VOLUME))