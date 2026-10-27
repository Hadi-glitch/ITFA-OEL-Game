KARACHI KINETIC RICKSHAW - how to run
1. Install Python 3.10+ and Pygame:   py -3.13 -m pip install pygame
2. Keep the assets/vehicles folder next to main.py.
3. Run:   py -3.13 main.py

Controls: D/Right gas | A/Left brake+reverse | Space/W/Up jump | R restart | Esc pause
Garage: Left/Right browse, Enter buy/select, Esc back.
Map screen: Left/Right choose, Enter drive.

Powerups (collectible glowing diamonds on the road):
  SPEED  - 1.4x top speed for 5 seconds (cyan)
  REGEN  - restores 30 HP over 4 seconds (pink)
  SHIELD - no damage for 4 seconds (gold)
  MAGNET - auto-collect nearby coins for 6 seconds (purple)
  2x     - double coin value for 8 seconds (orange)

Music: drop .ogg / .mp3 / .wav files into assets/sounds/music/ for background tracks.
       Volume is controlled in the Options menu (SFX and Music separately).

Save file: save.json (delete it to reset money and vehicles).
For testing set START_WALLET in settings.py and delete save.json.

ITFA Project | Python + Pygame
