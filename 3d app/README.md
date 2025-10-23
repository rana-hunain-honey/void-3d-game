Red Void — Ursina prototype

This is a Python/Ursina port of the `red_void.html` three.js prototype.

Quick start (Windows PowerShell):

1. Create a venv and activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r requirements.txt
```

3. Run the prototype:

```powershell
python main.py
```

Controls:
- WASD / Arrow keys: move
- Left click / Space: shoot
- P: Pre-warm Pools
- T: Trim Pools

Notes:
- This is an initial port focusing on functionality parity: player, enemies, pools, spawn logic, particles, and settings persistence.
- Audio is left as placeholders (Ursina can play WAV files if you add them and call `Audio()` in places where JS used WebAudio).
