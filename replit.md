# Red Void - 3D Survival Shooter

## Overview
Red Void is a 3D first-person survival shooter game built with Python and the Ursina game engine. Players navigate a neon grid environment, shooting at incoming enemies to survive as long as possible.

## Project Structure
- **3d app/main.py**: Main Python/Ursina game implementation
- **3d app/red_void.html**: Alternative Three.js browser-based version
- **3d app/requirements.txt**: Python dependencies (ursina)
- **3d app/settings.json**: Game settings persistence
- **3d app/*.wav**: Sound effects for shooting and kills

## Technology Stack
- **Language**: Python 3.11
- **Game Engine**: Ursina (built on Panda3D)
- **Alternative**: Three.js (HTML version)

## Game Features
- First-person shooter mechanics
- Object pooling for performance optimization
- Adaptive spawn system based on FPS
- Neon grid aesthetic
- Settings persistence (shadows, particles, sound)
- Mouse-based aiming with pointer lock
- Free-look mode

## Controls
- WASD / Arrow keys: Move
- Mouse: Aim
- Left Click / Space: Shoot
- F: Toggle free look
- P: Pre-warm object pools
- T: Trim object pools

## Recent Changes
- Initial project setup on Replit (October 23, 2025)
- Installed Python 3.11 and Ursina dependencies
- Created .gitignore for Python projects
- Created HTTP server (`server.py`) to serve the HTML/Three.js version
- Added landing page (`3d app/index.html`) with game information
- Configured workflow to run web server on port 5000
- Fixed JavaScript initialization bug in `red_void.html` (moved settings declaration before init())
- Converted line endings from Windows (CRLF) to Unix (LF) format
- Configured deployment for autoscale hosting

## Deployment Setup
- **Server**: Simple Python HTTP server serving static files
- **Port**: 5000 (required for Replit)
- **Entry Point**: `server.py`
- **Game Access**: `/red_void.html` or landing page at `/`

## Notes
- Ursina creates a desktop window and requires a display server (X11/Wayland)
- The Python/Ursina version cannot run in Replit's web environment without VNC
- Using the HTML/Three.js version for web deployment instead
- The HTML version uses Three.js r158 from CDN for 3D rendering
- All game files are served from the `3d app/` directory
