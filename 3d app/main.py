from ursina import *
import json
import os
import random
import math
import time as pytime
try:
    import winsound
except Exception:
    winsound = None
import wave
import struct

# === Configuration ===
SPAWN_SEC = 3.0
MAX_ENEMIES = 200
ENEMY_SPEED = 2.6
ENEMY_TURN_RATE = 180.0  # degrees per second for steering
FIREBALL_SPEED = 180.0
PLAYER_SPEED = 4.8
PLAYER_RADIUS = 0.35
WORLD_RADIUS = 30
POOL_MAX = 300

SETTINGS_FILE = 'settings.json'

# === Settings persistence ===
default_settings = {
    'shadows': True,
    'particles': True,
    'sound': True,
    'spawn_multiplier': 1.0,
    'enemy_speed_multiplier': 1.0,
}
if os.path.exists(SETTINGS_FILE):
    try:
        settings = json.load(open(SETTINGS_FILE))
    except Exception:
        settings = default_settings.copy()
else:
    settings = default_settings.copy()

# === App ===
app = Ursina()
window.title = 'Red Void — Ursina Prototype'
window.borderless = False
window.fullscreen = False
window.color = color.black

# camera
camera.fov = 70
camera.y = 2

# score and UI
score = 0
score_text = Text(text=f'Kills: {score}', position=window.top_left + (0.08, -0.04), scale=2, origin=(0,0), color=color.azure)
fps_text = Text(text='', position=window.top_right + (-0.26, -0.04), scale=2, origin=(0,0), color=color.green)

# Pools
enemy_pool = []
fireball_pool = []
particles_pool = []
particles_active = []

enemies = []
fireballs = []

# Player
player = Entity(model='cube', color=color.light_gray, scale=(0.5,0.3,0.9), position=(0,0,0))
player.rotation_z = 90
# hide visible player model for first-person view (we keep the entity for movement)
player.visible = False

# attach camera to player to make movement first-person
camera.parent = player
camera.position = (0, 1.6, 0)
camera.rotation = (0,0,0)

# base camera local position (for bobbing)
camera_base_pos = Vec3(*camera.position)

# mouse sensitivity
MOUSE_SENS = 60.0
MOUSE_SMOOTH = 12.0

# simple weapon model (first-person view)
weapon = Entity(parent=camera, model='cube', color=color.dark_gray, scale=(0.12,0.06,0.36), position=(0.28,-0.18,0.6), rotation=(0,8,4))

# crosshair defaults
crosshair_default_scale = 0.02

# simple crosshair
crosshair = Entity(parent=camera.ui, model='quad', color=color.rgb(255,60,60), scale=(0.02,0.02), position=(0,0))

# HUD indicator for mouse lock
mouse_lock_text = Text(text='', position=window.bottom_right + (-0.28, 0.04), scale=1.2, color=color.azure)

# neon grid: create tiled quads (cheap and simple)
GRID_SIZE = 40
GRID_DIVS = 20
grid_parent = Entity()
line_entities = []
for i in range(GRID_DIVS+1):
    t = i / GRID_DIVS * GRID_SIZE - GRID_SIZE/2
    # vertical
    e = Entity(parent=grid_parent, model='cube', color=color.rgb(255,40,40), scale=(0.02,0.001,GRID_SIZE), position=(t,-1.19,0))
    line_entities.append(e)
    # horizontal
    e2 = Entity(parent=grid_parent, model='cube', color=color.rgb(255,40,40), scale=(GRID_SIZE,0.001,0.02), position=(0,-1.19,t))
    line_entities.append(e2)

# light flash
flash_light = Entity(model='sphere', color=color.red, scale=0.1, enabled=False)

# free look / mouse state
free_look = False
right_mouse_look = False
player_yaw = 0.0
free_look_indicator = Text(text='Free Look: OFF (F)', position=window.bottom_left + (0.08, 0.04), scale=1.25, color=color.azure)

# FPS/adaptive spawn tracking
_fps_accum = 0.0
_fps_count = 0
_last_fps_check = pytime.time()

# audio files (generate simple beeps if missing)
SHOT_WAV = 'shot.wav'
KILL_WAV = 'kill.wav'
shot_snd = None
kill_snd = None

def generate_sine_wav(path, freq=440.0, duration=0.08, volume=0.2, samplerate=22050):
    n_samples = int(samplerate * duration)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        max_amp = 32767 * volume
        for i in range(n_samples):
            t = float(i) / samplerate
            val = int(max_amp * math.sin(2.0 * math.pi * freq * t))
            wf.writeframes(struct.pack('<h', val))

def ensure_audio():
    global shot_snd, kill_snd
    if not os.path.exists(SHOT_WAV):
        generate_sine_wav(SHOT_WAV, freq=880.0, duration=0.06, volume=0.18)
    if not os.path.exists(KILL_WAV):
        generate_sine_wav(KILL_WAV, freq=540.0, duration=0.09, volume=0.24)
    try:
        shot_snd = Audio(SHOT_WAV, autoplay=False)
        kill_snd = Audio(KILL_WAV, autoplay=False)
    except Exception:
        shot_snd = None
        kill_snd = None

ensure_audio()


# helpers
clock = time
spawn_interval_ms = int(max(200, SPAWN_SEC * 1000) / max(0.0001, settings.get('spawn_multiplier',1)))
last_spawn_time = 0

# pooling functions
def prefill_pools():
    for i in range(40):
        if len(enemy_pool) < POOL_MAX:
            e = Entity(model='cube', color=color.red, scale=(0.9,1.2,0.4), enabled=False)
            enemy_pool.append(e)
        if len(fireball_pool) < 80:
            f = Entity(model='sphere', color=color.rgb(255,102,102), scale=0.18, enabled=False)
            fireball_pool.append(f)
        if len(particles_pool) < 80:
            p = Entity(model='sphere', color=color.rgb(255,68,68), scale=0.03, enabled=False)
            particles_pool.append(p)

def trim_pools():
    # keep small reserve
    reserve_enemies = 20
    while len(enemy_pool) > reserve_enemies:
        e = enemy_pool.pop()
        e.disable()
        destroy(e)
    reserve_fire = 20
    while len(fireball_pool) > reserve_fire:
        f = fireball_pool.pop()
        f.disable()
        destroy(f)

# spawn enemy
def spawn_enemy():
    if len(enemies) >= MAX_ENEMIES:
        return
    # pick position on sphere-ish
    theta = random.uniform(0, 2*pi)
    phi = random.uniform(-0.6, 0.6)
    x = (WORLD_RADIUS + random.uniform(0,4)) * math.cos(theta) * math.cos(phi)
    z = (WORLD_RADIUS + random.uniform(0,4)) * math.sin(theta) * math.cos(phi)
    y = math.sin(phi) * (WORLD_RADIUS*0.2)
    if enemy_pool:
        e = enemy_pool.pop()
        e.position = (x, 0, z)
        e.enabled = True
    else:
        e = Entity(model='cube', color=color.red, scale=(0.9,1.2,0.4), position=(x,0,z))
    # store speed; direction recomputed each frame toward the player
    speed = ENEMY_SPEED * settings.get('enemy_speed_multiplier',1.0)
    enemies.append({'ent': e, 'speed': speed})
    # flash
    invoke(lambda: flash(0.6), delay=0)

# shoot
def shoot():
    # spawn from camera (screen center) so shots come from the player's view
    if fireball_pool:
        f = fireball_pool.pop()
        f.position = camera.world_position + camera.forward * 0.6
        f.enabled = True
    else:
        f = Entity(model='sphere', color=color.rgb(255,102,102), scale=0.18, position=camera.world_position + camera.forward * 0.6)
    # velocity in forward direction of camera
    forward = camera.forward
    vel = forward * FIREBALL_SPEED
    fireballs.append({'ent': f, 'vel': vel, 'born': time.time()})
    # sound placeholder
    if settings.get('sound', True):
        if shot_snd:
            try: shot_snd.play()
            except: pass
        elif winsound:
            try: winsound.Beep(880, 60)
            except: pass
    # recoil: move weapon back and bump camera pitch slightly
    weapon.position += Vec3(0,0,-0.06)
    camera.rotation_x = max(-70, camera.rotation_x - 3.5)
    # pulse crosshair
    crosshair.scale = (crosshair.scale[0] * 0.5 + crosshair_default_scale * 3.5, crosshair.scale[1] * 0.5 + crosshair_default_scale * 3.5)

# simple flash effect
def flash(intensity):
    flash_light.enabled = True
    flash_light.scale = intensity * 0.3
    invoke(lambda: setattr(flash_light, 'enabled', False), delay=0.06)

# input
def input(key):
    if key == 'space' or key == 'left mouse down':
        shoot()
    if key == 'p':
        prefill_pools()
    if key == 't':
        trim_pools()
    if key == 'f':
        global free_look
        free_look = not free_look
        free_look_indicator.text = 'Free Look: ' + ('ON' if free_look else 'OFF') + ' (F)'

# UI buttons
Button(text='Pre-warm Pools (P)', color=color.black, scale=(0.12,0.05), position=window.top_right + (-0.12, -0.06), on_click=lambda: prefill_pools())
Button(text='Trim Pools (T)', color=color.black, scale=(0.12,0.05), position=window.top_right + (-0.12, -0.12), on_click=lambda: trim_pools())
Button(text='Verify Pools', color=color.black, scale=(0.12,0.05), position=window.top_right + (-0.12, -0.18), on_click=lambda: verify_pools())

# settings save every now and then
save_timer = 0

def update():
    global last_spawn_time, score, save_timer
    dt = time.dt
    # snap grid to camera world x/z so the grid stays centered under player
    cam_x = int(math.floor(camera.world_x / (GRID_SIZE / GRID_DIVS))) * (GRID_SIZE / GRID_DIVS)
    cam_z = int(math.floor(camera.world_z / (GRID_SIZE / GRID_DIVS))) * (GRID_SIZE / GRID_DIVS)
    grid_parent.x = cam_x
    grid_parent.z = cam_z

    # simple movement WASD (relative to camera yaw)
    move_dir = Vec3(0,0,0)
    yaw = camera.rotation_y
    forward = Vec3(math.sin(math.radians(yaw)), 0, math.cos(math.radians(yaw)))
    right = Vec3(forward.z, 0, -forward.x)
    if held_keys['w'] or held_keys['up arrow']:
        move_dir += forward
    if held_keys['s'] or held_keys['down arrow']:
        move_dir -= forward
    if held_keys['a'] or held_keys['left arrow']:
        move_dir -= right
    if held_keys['d'] or held_keys['right arrow']:
        move_dir += right
    if move_dir.length_squared() > 0:
        move_dir = move_dir.normalized()
    player.position += move_dir * PLAYER_SPEED * dt

    # camera bob when moving
    move_speed = move_dir.length()
    bob_x = math.sin(pytime.time() * 8.0) * 0.004 * move_speed
    bob_y = math.cos(pytime.time() * 8.0) * 0.008 * move_speed
    camera.position = camera_base_pos + Vec3(bob_x, bob_y, 0)
    weapon.x = 0.28 + bob_x * 3.0
    weapon.y = -0.18 + bob_y * 2.0
    # crosshair damping towards default
    crosshair.scale = (crosshair.scale[0] * 0.85 + crosshair_default_scale * 0.15, crosshair.scale[1] * 0.85 + crosshair_default_scale * 0.15)

    # spawn logic
    if time.time() - last_spawn_time > max(0.2, SPAWN_SEC / max(0.0001, settings.get('spawn_multiplier',1))):
        spawn_enemy()
        last_spawn_time = time.time()

    # update fireballs
    for fb in list(fireballs):
        ent = fb['ent']
        ent.position += fb['vel'] * dt
        # lifetime
        if time.time() - fb['born'] > 4.0:
            try:
                fireballs.remove(fb)
            except:
                pass
            if len(fireball_pool) < POOL_MAX:
                fb['ent'].enabled = False
                fireball_pool.append(fb['ent'])
            else:
                destroy(fb['ent'])

    # update enemies: steer toward the player's current position
    for en in list(enemies):
        ent = en['ent']
        # vector to player
        to_player = (player.position - ent.position)
        if to_player.length_squared() > 0.0001:
            desired_dir = to_player.normalized()
            # initialize forward if missing
            if 'forward' not in en:
                en['forward'] = Vec3(0,0,1)
            cur_fwd = en['forward']
            # clamp dot product for numeric safety
            dot = clamp(cur_fwd.dot(desired_dir), -1.0, 1.0)
            angle = math.degrees(math.acos(dot))
            max_turn = ENEMY_TURN_RATE * dt
            if angle > 0.001:
                t = min(1.0, max_turn / max(1e-6, angle))
                new_fwd = lerp(cur_fwd, desired_dir, t).normalized()
                en['forward'] = new_fwd
            else:
                new_fwd = cur_fwd
            vel = new_fwd * en.get('speed', ENEMY_SPEED)
            ent.position += vel * dt
        # simple collision distance
        if distance(ent.position, player.position) < 1.0:
            # end game: show message
            invoke(lambda: application.quit(), delay=0.1)
            return
        # check collisions with fireballs
        for fb in list(fireballs):
            if distance(ent.position, fb['ent'].position) < 1.2:
                # kill
                try:
                    enemies.remove(en)
                except:
                    pass
                try:
                    fireballs.remove(fb)
                except:
                    pass
                # spawn particles (simple enable/disable)
                if particles_pool:
                    # spawn multiple small particles with velocities
                    for n in range(6):
                        if not particles_pool: break
                        p = particles_pool.pop()
                        p.position = ent.position
                        p.enabled = True
                        # attach velocity and born time
                        p.vel = Vec3(random.uniform(-1,1), random.uniform(0,1), random.uniform(-1,1)) * 3.0
                        p.born = pytime.time()
                        particles_active.append(p)
                # return to pools
                if len(enemy_pool) < POOL_MAX:
                    ent.enabled = False
                    enemy_pool.append(ent)
                else:
                    destroy(ent)
                if len(fireball_pool) < POOL_MAX:
                    fb['ent'].enabled = False
                    fireball_pool.append(fb['ent'])
                else:
                    destroy(fb['ent'])
                score += 1
                score_text.text = f'Kills: {score}'
                # play kill sound
                if settings.get('sound', True):
                    if kill_snd:
                        try: kill_snd.play()
                        except: pass
                    elif winsound:
                        try: winsound.Beep(540, 80)
                        except: pass
                break
        # remove if close to origin
        if ent.position.length() < 0.1:
            try:
                enemies.remove(en)
            except:
                pass
            if len(enemy_pool) < POOL_MAX:
                ent.enabled = False
                enemy_pool.append(ent)
            else:
                destroy(ent)

    # fps display
    fps_text.text = f'FPS: {int(1/max(1e-6, dt))} • Enemies: {len(enemies)}'

    # adaptive spawn: sample FPS once per second
    global _fps_accum, _fps_count, _last_fps_check
    _fps_accum += (1.0 / max(1e-6, dt))
    _fps_count += 1
    now = pytime.time()
    if now - _last_fps_check > 1.0:
        avg_fps = _fps_accum / max(1, _fps_count)
        _fps_accum = 0.0; _fps_count = 0; _last_fps_check = now
        # if avg fps drops below 30, conservative throttle
        if avg_fps < 30:
            settings['_adaptive'] = min(4.0, settings.get('_adaptive', 1.0) * 1.15)
            settings['spawn_multiplier'] = max(0.2, settings.get('spawn_multiplier',1.0) / settings['_adaptive'])
            # restart spawn interval
            # note: last_spawn_time reset to avoid immediate spawn
            last_spawn_time = now
        elif avg_fps > 45 and settings.get('_adaptive',1.0) > 1.01:
            settings['_adaptive'] = max(1.0, settings.get('_adaptive',1.0) / 1.15)
            settings['spawn_multiplier'] = min(2.0, settings.get('spawn_multiplier',1.0) / settings.get('_adaptive',1.0))
            last_spawn_time = now

    # periodic save
    save_timer += dt
    if save_timer > 3.0:
        save_timer = 0
        json.dump(settings, open(SETTINGS_FILE, 'w'))

    # update particles with simple physics
    for p in list(particles_active):
        t = pytime.time() - p.born
        p.position += p.vel * dt
        p.vel *= 0.92
        if t > 0.6:
            try:
                particles_active.remove(p)
            except:
                pass
            p.enabled = False
            if len(particles_pool) < 200:
                particles_pool.append(p)
            else:
                destroy(p)

# mouse handling: simple pointer lock and right-click free-look
def input(key):
    # central input handler: shooting, pool controls, and free-look/mouse lock
    global free_look, right_mouse_look
    if key == 'left mouse down' or key == 'space':
        shoot()
    if key == 'p':
        prefill_pools()
    if key == 't':
        trim_pools()
    if key == 'f':
        # toggle free-look + lock pointer when enabled
        free_look = not free_look
        mouse.locked = bool(free_look)
        free_look_indicator.text = 'Free Look: ' + ('ON' if free_look else 'OFF') + ' (F)'
    if key == 'right mouse down':
        right_mouse_look = True
        mouse.locked = True
    if key == 'right mouse up':
        right_mouse_look = False
        # only unlock if free_look is not active
        if not free_look:
            mouse.locked = False

def update_camera_rotation():
    # rotate camera by mouse delta when free-look or right mouse held
    if mouse.locked or free_look:
        dx = mouse.velocity[0]
        dy = mouse.velocity[1]
        sensitivity = MOUSE_SENS
        # apply rotation with smoothing factor
        camera.rotation_y += dx * sensitivity * time.dt * (MOUSE_SMOOTH * time.dt + 1.0)
        camera.rotation_x -= dy * sensitivity * time.dt * (MOUSE_SMOOTH * time.dt + 1.0)
        camera.rotation_x = clamp(camera.rotation_x, -70, 70)
    # relax weapon recoil back to resting position
    weapon.position = weapon.position * 0.85 + Vec3(0.28, -0.18, 0.6) * 0.15

# call camera rotation each frame
old_update = update
def _update_wrapper():
    old_update()
    update_camera_rotation()
globals()['update'] = _update_wrapper

def verify_pools():
    # quick sanity check: count pool sizes and display via flash
    total = len(enemy_pool) + len(fireball_pool) + len(particles_pool)
    print(f'Pools: enemies={len(enemy_pool)} fireballs={len(fireball_pool)} particles={len(particles_pool)} total={total}')
    flash(0.4)

# prefill a bit
prefill_pools()

if __name__ == '__main__':
    app.run()
