# Red Void — Project Overview

This repository contains two implementations of a prototype 3D survival shooter called *Red Void*:

1. `3d app/red_void.html` — Browser/Three.js implementation (recommended for web).
2. `3d app/main.py` — Python/Ursina implementation (desktop; requires Ursina and a display).

Quick run (web version)

1. Start the local static server:

```powershell
python server.py
```

2. Open the game in a browser:

```
http://localhost:5000/red_void.html
```

Quick run (Ursina Python version)

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r "3d app\requirements.txt"
```

3. Run the Ursina prototype:

```powershell
python "3d app\main.py"
```

Notes and changes I made

- Fixed settings file load/save in `3d app/main.py` to use safe context managers.
- Removed a duplicate `input(key)` handler in `3d app/main.py` to avoid accidental override.
- Replaced fragile `.dispose()` calls in `3d app/red_void.html` with safer checks before calling `dispose()` to avoid runtime errors in some browsers.
- Started the local server (`server.py`) in the workspace; it serves the web game at port 5000.
- Tested Python import of `ursina` in the workspace Python; import failed (module not installed in the current environment).

If you want, I can:
- Install `ursina` into a virtualenv here and run the Ursina prototype (note: rendering requires a GUI/display environment).
- Add automated tests or a small CI job.
- Create a small script to launch either version more conveniently.

Tell me what to do next.