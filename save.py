# save.py - tiny JSON save file (wallet, owned vehicles, selections, best distances).
import json
import os
import settings as S

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), S.SAVE_FILE)


def default():
    """A brand-new save: starter vehicle only, first map."""
    return {"wallet": S.START_WALLET, "owned": ["classic"], "vehicle": "classic",
            "map": "university", "best": {}, "powerup_levels": {}}


def load():
    """Read the save file; fall back to a fresh save if it is missing or broken."""
    data = default()
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            data.update(json.load(f))
    except (OSError, ValueError):
        pass
    if "classic" not in data["owned"]:
        data["owned"].append("classic")
    return data


def write(data):
    """Write the save file; ignore errors (e.g. read-only folder) so the game never crashes."""
    try:
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


def reset():
    """Reset the save file to brand-new defaults and write it to disk."""
    data = default()
    write(data)
    return data
