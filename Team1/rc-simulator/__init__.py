"""Rotor: an RC car racer for the GitHub Universe 2026 badge.

Race a twisty circuit against five CPU cars. Beat the clock, beat the CPUs.

Controls
  UP        accelerate        (right side)
  DOWN      brake, then reverse
  A         steer left        (bottom row)
  C         steer right
  B         start the race; at any time, back to the start screen

The car is loaded from a car folder (parameters.txt, .obj meshes, car.bmp);
see CAR_FILES_LOOSE / CAR_DIR below. Without one, a simple box car is used.
"""

import gc
import math
import micropython
import os
import random
import sys

# ---------------------------------------------------------------------------
# Paths: all file access is by absolute path under APP_DIR. The cwd is only a
# last-resort fallback; os.getcwd() can raise EIO on the badge's FAT volume.
# ---------------------------------------------------------------------------

APP_NAME = "rc-simulator"
APP_ROOTS = ("/remote/apps", "/system/apps", "/apps", "")
APP_MARKERS = ("carmodel.py", "track.py")   # files that identify the app folder


def _cwd():
    """os.getcwd(), or "" when the filesystem can't answer."""
    try:
        return os.getcwd()
    except OSError:
        return ""


def _join(*parts):
    """Join path parts into one absolute path: _join("/a/", "b") == "/a/b"."""
    return "/" + "/".join(p.strip("/") for p in parts if p and p.strip("/"))


def _norm(path):
    """Absolute form of path, without ".", ".." or doubled slashes."""
    if not path.startswith("/"):
        path = _cwd() + "/" + path
    out = []
    for part in path.split("/"):
        if part == "..":
            if out:
                out.pop()
        elif part and part != ".":
            out.append(part)
    return "/" + "/".join(out)


def _is_app_dir(path):
    for name in APP_MARKERS:
        try:
            os.stat(_join(path, name))
        except OSError:
            return False
    return True


def _find_app_dir():
    # __file__'s folder, then the standard install paths
    candidates = []
    here = globals().get("__file__", "")
    if "/" in here:
        candidates.append(_norm(here.rsplit("/", 1)[0] or "/"))
    for root in APP_ROOTS:
        candidates.append(_join(root, APP_NAME))
    for path in candidates:
        if _is_app_dir(path):
            return path
    # renamed install: any app folder containing APP_MARKERS
    for root in APP_ROOTS:
        try:
            entries = os.listdir(root or "/")
        except OSError:
            continue
        for entry in entries:
            path = _join(root, entry)
            if _is_app_dir(path):
                return path
    # root (web simulator upload), then the cwd
    for path in ("/", _cwd()):
        if path and _is_app_dir(path):
            return _norm(path)
    return _join("/system/apps", APP_NAME)


APP_DIR = _find_app_dir()


def app_path(*parts):
    """Absolute path to a file in this app's folder."""
    return _join(APP_DIR, *parts)


# carmodel and track import from APP_DIR
sys.path.insert(0, APP_DIR)
try:
    os.chdir(APP_DIR)
except OSError:
    pass

import carmodel
import track as trackmod

try:
    from badgeware import State
except ImportError:
    State = None

screen.font = font.sins
screen.antialias = image.X2

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# Car files (parameters.txt, *.obj, car.bmp): loose in APP_DIR or in CAR_DIR.
# Both are searched; CAR_FILES_LOOSE = True tries the loose files first.
CAR_FILES_LOOSE = True
CAR_DIR = "assets/gravelbasher"
DEFAULT_CAR_NAME = "Gravel Basher"
CACHE_DIR = "/state"

LAPS = 3                 # laps per race
CPU_COUNT = 5
PLAYER_SLOT = 4          # grid slot 0..5 (2 per row); 4 = back row, left

# Intro slides: fade time and how long each slide holds, ms
FADE_MS = 600
SLIDE_HOLD_MS = (2600, 2200, 3200)

# Rendering
FAR = 18.0               # draw distance, m
KERBS = True             # red/white kerbs on corners
SMALL_PART_FACES = 12    # faces kept per small non-wheel part (lights, spoilers)
SHOW_FPS = False         # frames per second, top right

# CPU cars are pre-rendered sprites, SPRITE_ANGLES headings per distance band.
# Band: (used from distance m, render distance m, camera elevation of distance m)
SPRITE_ANGLES = 32
SPRITE_SETS = (
    (0.0, 0.9, 0.9),
    (1.1, 1.1, 1.32),
    (1.7, 1.7, 2.04),
    (3.0, 3.0, 3.6),
)

# Buttons: A B C along the bottom, UP/DOWN on the right side.
# Prefer BUTTON_A/B/C; fall back to the logical names some firmware uses.
def _button(*names):
    for name in names:
        try:
            return eval(name)  # runtime constants may be globals or builtins
        except NameError:
            pass
    return None


BTN_UP = _button("BUTTON_UP")
BTN_DOWN = _button("BUTTON_DOWN")
BTN_A = _button("BUTTON_A", "BUTTON_LEFT")
BTN_B = _button("BUTTON_B", "BUTTON_SELECT")
BTN_C = _button("BUTTON_C", "BUTTON_RIGHT")


def held(button):
    return button is not None and badge.held(button)


def pressed(button):
    return button is not None and badge.pressed(button)


def rand(lo, hi):
    return lo + (hi - lo) * random.random()


# ---------------------------------------------------------------------------
# Handling. A loaded car's parameters.txt overrides these defaults.
# Units are metres and seconds; the speedo is scaled to the car's top end.
# ---------------------------------------------------------------------------

TOP_END_MPH = 34.4   # TopEnd: speedo at top speed
STEER_RATE = 2.5     # SteerRate
STEER_MOD = 0.4      # SteerMod (less lock at speed)
ENGINE_RATE = 4.5    # EngineRate
MAX_STEER = 0.35     # rad of front wheel lock (SteerRatio)
WHEELBASE = 0.26     # m (from wheel Offset1)

SIM_PER_MPH = 8.0 / 34.4   # sim m/s per speedo mph
TOP_SPEED = TOP_END_MPH * SIM_PER_MPH
REV_SPEED = 3.0
ACCEL = 7.0
BRAKE = 14.0
COAST = 2.0
GRIP_TURN = 12.0
GRIP_SLIDE = 9.0
YAW_RESPONSE = 10.0

GRASS_TOP = 0.45     # top speed multiplier off the track
GRASS_GRIP = 0.7
GRASS_DRAG = 5.0     # m/s^2 extra slowdown on grass

CAR_RADIUS = 0.2     # for car-to-car bumps


def apply_tune(t):
    global TOP_END_MPH, STEER_RATE, STEER_MOD, ENGINE_RATE, MAX_STEER
    global WHEELBASE, TOP_SPEED, ACCEL

    def pick(key, lo, hi, cur):
        v = t.get(key)
        if v is None or v <= 0:
            return cur
        return min(hi, max(lo, v))

    TOP_END_MPH = pick("top_end", 5, 90, TOP_END_MPH)
    STEER_RATE = pick("steer_rate", 0.5, 10, STEER_RATE)
    ENGINE_RATE = pick("engine_rate", 0.5, 20, ENGINE_RATE)
    MAX_STEER = pick("max_steer", 0.15, 0.6, MAX_STEER)
    WHEELBASE = pick("wheelbase", 0.1, 0.5, WHEELBASE)
    v = t.get("steer_mod")
    if v is not None:
        STEER_MOD = min(0.9, max(0.0, v))
    TOP_SPEED = TOP_END_MPH * SIM_PER_MPH
    a = t.get("acc")
    if a:
        ACCEL = min(11.0, max(5.0, 4.5 + a * 0.6))


def sign(v):
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def approach(cur, dest, step):
    if dest > cur:
        return dest if dest - cur < step else cur + step
    if dest < cur:
        return dest if cur - dest < step else cur - step
    return cur


def ease_steer(cur, dest, dt):
    # snap back to centre (and counter-steer) quickly, wind on lock slowly
    step = STEER_RATE * dt
    if dest == 0 or sign(dest) != sign(cur):
        step *= 4
    else:
        step *= 0.5
    return approach(cur, dest, step)


def ease_volt(cur, dest, dt):
    # the motor drops to zero before it can reverse direction
    if (dest < 0 < cur) or (dest > 0 > cur):
        cur = 0.0
    return approach(cur, dest, ENGINE_RATE * dt)


class Car:
    def __init__(self, name, cpu, tag_pen):
        self.name = name
        self.cpu = cpu
        self.tag_pen = tag_pen
        self.tag_img = tag_image(tag_pen) if cpu else None
        self.top_scale = 1.0
        self.acc_scale = 1.0

    def place(self, dist, lateral):
        s = dist % TRACK.length
        self.x, self.z, self.yaw = TRACK.pose_at(s, lateral)
        self.vx = 0.0        # world velocity
        self.vz = 0.0
        self.vf = 0.0        # forward speed in the car frame
        self.yaw_rate = 0.0
        self.steer = 0.0     # -1 .. 1
        self.volt = 0.0      # -1 .. 1
        self.wheel = 0.0     # front wheel angle, for drawing
        self.dist = dist     # race distance, m (negative on the grid)
        self.s_local = s
        self.idx = TRACK.point_at(s)
        self.off = False
        self.done = False
        self.time = None
        self.brake = False
        self.laps_done = 0   # laps completed
        self.lap_start = 0   # race_ms when the current lap began
        self.best_lap = None # fastest completed lap this race, ms
        # CPU personality
        self.lane = 0.0
        self.lane_target = 0.0
        self.lane_t = 0.0
        self.wobble = 0.0
        self.wobble_target = 0.0
        self.wobble_t = 0.0
        self.stuck_t = 0.0
        self.reverse_t = 0.0

    def update(self, dt, throttle, steer_in):
        self.steer = ease_steer(self.steer, steer_in, dt)
        self.volt = ease_volt(self.volt, throttle, dt)

        top = TOP_SPEED * self.top_scale
        accel = ACCEL * self.acc_scale
        grip = GRIP_TURN
        if self.off:
            top *= GRASS_TOP
            accel *= 0.7
            grip *= GRASS_GRIP

        s = math.sin(self.yaw)
        c = math.cos(self.yaw)
        vf = self.vx * s + self.vz * c
        vl = self.vx * c - self.vz * s

        v = self.volt
        if self.brake:
            a = -sign(vf) * BRAKE * 0.5
            if abs(vf) < BRAKE * dt:
                a = 0.0
                vf = 0.0
        elif v > 0:
            a = BRAKE * v if vf < -0.05 else accel * v * (1 - vf / top)
        elif v < 0:
            a = BRAKE * v if vf > 0.05 else accel * v * (1 + vf / REV_SPEED)
        else:
            a = -sign(vf) * COAST
            if abs(vf) < COAST * dt:
                a = 0.0
                vf = 0.0
        if self.off and abs(vf) > top:
            a -= sign(vf) * GRASS_DRAG
        vf += a * dt

        speed_frac = min(1.0, abs(vf) / TOP_SPEED)
        self.wheel = self.steer * MAX_STEER * (1 - STEER_MOD * speed_frac)
        target = vf * math.tan(self.wheel) / WHEELBASE
        limit = grip / max(abs(vf), 0.5)
        if target > limit:
            target = limit
        elif target < -limit:
            target = -limit
        self.yaw_rate += (target - self.yaw_rate) * min(1.0, YAW_RESPONSE * dt)

        scrub = GRIP_SLIDE * dt
        vl = 0.0 if abs(vl) <= scrub else vl - sign(vl) * scrub

        # Rebuild world velocity on the old heading, then rotate the body.
        # Velocity lags the heading, which is what makes the car slide.
        self.vx = vf * s + vl * c
        self.vz = vf * c - vl * s
        self.vf = vf
        self.yaw += self.yaw_rate * dt
        self.x += self.vx * dt
        self.z += self.vz * dt


# ---------------------------------------------------------------------------
# Track and race progress
# ---------------------------------------------------------------------------

TRACK = trackmod.Track()
RACE_DIST = TRACK.finish + (LAPS - 1) * TRACK.length   # grid to chequered flag, m


def laps_done(car):
    if car.dist < TRACK.finish:
        return 0
    return int((car.dist - TRACK.finish) // TRACK.length) + 1


def lap_of(car):
    """The lap a car is on, 1..LAPS."""
    if car.dist < TRACK.finish:
        return 1
    return min(LAPS, int((car.dist - TRACK.finish) // TRACK.length) + 2)
RECOVER_DIST = 2.5   # beyond this from the centreline, progress stops counting


def track_car(car):
    t = TRACK
    j, d2 = t.nearest(car.x, car.z, car.idx)
    hw = t.half[j]
    lat = t.lateral(car.x, car.z, j)
    car.off = abs(lat) > hw + 0.05
    if d2 > (hw + RECOVER_DIST) * (hw + RECOVER_DIST):
        car.off = True
        return  # too far away: no progress until back on the track
    along = (car.x - t.x[j]) * t.dx[j] + (car.z - t.z[j]) * t.dz[j]
    s = t.s[j] + along
    ds = s - car.s_local
    half_len = t.length / 2
    if ds > half_len:
        ds -= t.length
    elif ds < -half_len:
        ds += t.length
    car.dist += ds
    car.s_local = s
    car.idx = j


def cpu_drive(car, dt):
    t = TRACK
    # pick a new line every few seconds, and wobble a bit like a real driver
    car.lane_t -= dt
    if car.lane_t <= 0:
        car.lane_target = rand(-0.55, 0.55)
        car.lane_t = rand(1.5, 4.0)
    car.lane += (car.lane_target - car.lane) * min(1.0, dt * 0.8)
    car.wobble_t -= dt
    if car.wobble_t <= 0:
        if random.random() < 0.12:
            car.wobble_target = rand(-0.9, 0.9)   # the occasional mistake
            car.wobble_t = rand(0.25, 0.5)
        else:
            car.wobble_target = rand(-0.2, 0.2)
            car.wobble_t = rand(0.4, 1.5)
    car.wobble += (car.wobble_target - car.wobble) * min(1.0, dt * 4)

    look = 1.2 + abs(car.vf) * 0.45
    s_t = car.s_local + look
    i_t = t.point_from(car.idx, s_t)
    tx, tz, _ = t.pose_at(s_t, car.lane * t.half[i_t], i_t)
    dx = tx - car.x
    dz = tz - car.z
    sy = math.sin(car.yaw)
    cy = math.cos(car.yaw)
    lx = dx * cy - dz * sy
    lz = dx * sy + dz * cy
    ang = math.atan2(lx, lz)
    steer = max(-1.0, min(1.0, ang * 2.2 + car.wobble))

    k = t.ahead[car.idx]
    vmax = math.sqrt(GRIP_TURN * 0.85 / k) if k > 0 else 99.0
    vt = min(TOP_SPEED * car.top_scale, vmax)
    if car.vf < vt:
        throttle = 1
    elif car.vf > vt * 1.12:
        throttle = -1
    else:
        throttle = 0

    # unstick: back up for a moment if stopped against something
    if car.reverse_t > 0:
        car.reverse_t -= dt
        throttle = -1
        steer = -sign(ang)
    elif abs(car.vf) < 0.3:
        car.stuck_t += dt
        if car.stuck_t > 1.2:
            car.stuck_t = 0.0
            car.reverse_t = 0.9
    else:
        car.stuck_t = 0.0
    return throttle, steer


def bump_cars(cars):
    r2 = (2 * CAR_RADIUS) * (2 * CAR_RADIUS)
    n = len(cars)
    for i in range(n):
        a = cars[i]
        for j in range(i + 1, n):
            b = cars[j]
            dx = b.x - a.x
            dz = b.z - a.z
            d2 = dx * dx + dz * dz
            if d2 >= r2 or d2 == 0:
                continue
            d = math.sqrt(d2)
            nx = dx / d
            nz = dz / d
            push = (2 * CAR_RADIUS - d) / 2
            a.x -= nx * push
            a.z -= nz * push
            b.x += nx * push
            b.z += nz * push
            vn = (b.vx - a.vx) * nx + (b.vz - a.vz) * nz
            if vn < 0:
                j_imp = -0.65 * vn   # (1 + restitution) / 2 with restitution 0.3
                a.vx -= nx * j_imp
                a.vz -= nz * j_imp
                b.vx += nx * j_imp
                b.vz += nz * j_imp


# ---------------------------------------------------------------------------
# Camera and projection. Camera space: X right, Y up (relative to the
# camera), Z forward. Level pitch with the horizon shifted up.
# ---------------------------------------------------------------------------

SW = screen.width
SH = screen.height
FOCAL = SW * 0.72
CX = SW / 2
HY = int(SH * 0.30)
CAM_H = 0.40
CAM_DIST = 1.1
CAM_FOLLOW = 5.0
ORBIT_R = 1.3
ORBIT_SPEED = 0.55
Z_NEAR = 0.25
GROUND_K = FOCAL * CAM_H
FAR2 = FAR * FAR

SKY = color.rgb(120, 170, 235)
SKY_LOW = color.rgb(170, 205, 245)
GRASS = color.rgb(62, 128, 70)
GRASS_FAR = color.rgb(96, 150, 104)
ASPHALT_A = color.rgb(74, 78, 86)
ASPHALT_B = color.rgb(80, 84, 92)
KERB_RED = color.rgb(214, 48, 48)
KERB_WHITE = color.rgb(236, 236, 236)
LINE_WHITE = color.rgb(240, 240, 240)
CHECK_DARK = color.rgb(24, 24, 28)
SHADOW = color.rgb(16, 30, 20, 120)
POST = color.rgb(60, 64, 72)
HUD = color.rgb(255, 255, 255)
HUD_DIM = color.rgb(210, 220, 230)
HUD_WARN = color.rgb(255, 200, 120)
PANEL = color.rgb(13, 17, 23, 215)
PANEL_EDGE = color.rgb(48, 54, 61)
ACCENT = color.rgb(126, 231, 135)     # Universe-ish neon green
ACCENT_2 = color.rgb(188, 140, 255)   # and purple
TAG_PENS = (
    color.rgb(255, 123, 114),
    color.rgb(121, 192, 255),
    color.rgb(210, 168, 255),
    color.rgb(255, 166, 87),
    color.rgb(126, 231, 135),
)


def to_cam(x, z, camx, camz, c, s):
    dx = x - camx
    dz = z - camz
    return dx * c - dz * s, dx * s + dz * c


@micropython.native
def fill_ground(xs, zs, pen):
    """Clip a ground polygon (camera-space X/Z lists) at the near plane,
    project it and fill it as a triangle fan."""
    n = len(xs)
    out = []
    for k in range(n):
        x0 = xs[k]
        z0 = zs[k]
        k1 = k + 1 if k + 1 < n else 0
        x1 = xs[k1]
        z1 = zs[k1]
        in0 = z0 >= Z_NEAR
        if in0:
            out.append(vec2(CX + FOCAL * x0 / z0, HY + GROUND_K / z0))
        if in0 != (z1 >= Z_NEAR):
            t = (Z_NEAR - z0) / (z1 - z0)
            xi = x0 + (x1 - x0) * t
            out.append(vec2(CX + FOCAL * xi / Z_NEAR, HY + GROUND_K / Z_NEAR))
    m = len(out)
    if m < 3:
        return
    screen.pen = pen
    p0 = out[0]
    for k in range(1, m - 1):
        screen.triangle(p0, out[k], out[k + 1])


def draw_quad(ax, az, bx, bz, cx_, cz_, dx_, dz_, camx, camz, c, s, pen):
    ax, az = to_cam(ax, az, camx, camz, c, s)
    bx, bz = to_cam(bx, bz, camx, camz, c, s)
    cx_, cz_ = to_cam(cx_, cz_, camx, camz, c, s)
    dx_, dz_ = to_cam(dx_, dz_, camx, camz, c, s)
    fill_ground([ax, bx, cx_, dx_], [az, bz, cz_, dz_], pen)


def make_marks():
    """Start line, chequered finish line and grid boxes as ground quads."""
    t = TRACK
    quads = []

    def strip(s0, s1, lat0, lat1, pen):
        x0, z0, _ = t.pose_at(s0, lat0)
        x1, z1, _ = t.pose_at(s0, lat1)
        x2, z2, _ = t.pose_at(s1, lat1)
        x3, z3, _ = t.pose_at(s1, lat0)
        quads.append((x0, z0, x1, z1, x2, z2, x3, z3, pen,
                      (x0 + x2) / 2, (z0 + z2) / 2))

    hw = t.half[0]
    strip(-0.12, 0.12, -hw, hw, LINE_WHITE)                    # start line
    f = t.finish
    hw = t.half[t.point_at(f)]
    cols = 8
    for row in range(2):                                       # finish line
        for col in range(cols):
            lat0 = -hw + 2 * hw * col / cols
            lat1 = -hw + 2 * hw * (col + 1) / cols
            pen = CHECK_DARK if (row + col) % 2 else LINE_WHITE
            strip(f - 0.25 + row * 0.25, f + row * 0.25, lat0, lat1, pen)
    for slot in range(6):                                      # grid boxes
        d, lat = grid_pos(slot)
        strip(d + 0.26, d + 0.31, lat - 0.16, lat + 0.16, LINE_WHITE)
    return quads


def grid_pos(slot):
    row = slot // 2
    col = slot % 2
    d = -1.0 - row * 1.3 - col * 0.55
    lat = -0.6 if col == 0 else 0.6
    return d, lat


_N = TRACK.n
_CLX = [0.0] * _N    # camera-space edge points, refreshed per frame
_CLZ = [0.0] * _N
_CRX = [0.0] * _N
_CRZ = [0.0] * _N
_KLX = [0.0] * _N
_KLZ = [0.0] * _N
_KRX = [0.0] * _N
_KRZ = [0.0] * _N
_PL = [None] * _N    # screen-space edge points (None: behind the near plane)
_PR = [None] * _N
_PKL = [None] * _N
_PKR = [None] * _N
_KERB_PT = [KERBS and (TRACK.curv[i] > 0 or TRACK.curv[i - 1] > 0) for i in range(_N)]
_STAMP = [-1] * _N
_frame = [0]


def _near_lists():
    """_NEAR[i]: points within FAR + NEAR_SLACK + 2.5 m of point i
    (bytes when n <= 256)."""
    t = TRACK
    r = FAR + NEAR_SLACK + 2.5   # 2.5: longest segment
    r2 = r * r
    out = []
    for i in range(t.n):
        xi = t.x[i]
        zi = t.z[i]
        near = []
        for j in range(t.n):
            dx = t.x[j] - xi
            dz = t.z[j] - zi
            if dx * dx + dz * dz <= r2:
                near.append(j)
        out.append(bytes(near) if t.n <= 256 else near)
    return out


NEAR_SLACK = 6.0     # m; max camera distance from ref for _NEAR[ref] to apply
_ALL = list(range(_N))
_NEAR = []           # set at load by _near_lists()


@micropython.native
def _cam_point(i, camx, camz, c, s, frame):
    if _STAMP[i] == frame:
        return
    _STAMP[i] = frame
    t = TRACK
    dx = t.lx[i] - camx
    dz = t.lz[i] - camz
    x = dx * c - dz * s
    z = dx * s + dz * c
    _CLX[i] = x
    _CLZ[i] = z
    _PL[i] = vec2(CX + FOCAL * x / z, HY + GROUND_K / z) if z >= Z_NEAR else None
    dx = t.rx[i] - camx
    dz = t.rz[i] - camz
    x = dx * c - dz * s
    z = dx * s + dz * c
    _CRX[i] = x
    _CRZ[i] = z
    _PR[i] = vec2(CX + FOCAL * x / z, HY + GROUND_K / z) if z >= Z_NEAR else None
    if _KERB_PT[i]:
        dx = t.klx[i] - camx
        dz = t.klz[i] - camz
        x = dx * c - dz * s
        z = dx * s + dz * c
        _KLX[i] = x
        _KLZ[i] = z
        _PKL[i] = vec2(CX + FOCAL * x / z, HY + GROUND_K / z) if z >= Z_NEAR else None
        dx = t.krx[i] - camx
        dz = t.krz[i] - camz
        x = dx * c - dz * s
        z = dx * s + dz * c
        _KRX[i] = x
        _KRZ[i] = z
        _PKR[i] = vec2(CX + FOCAL * x / z, HY + GROUND_K / z) if z >= Z_NEAR else None


@micropython.native
def draw_ground(camx, camz, c, s, ref):
    screen.pen = SKY
    screen.rectangle(0, 0, SW, HY)
    screen.pen = SKY_LOW
    screen.rectangle(0, HY - 6, SW, 6)
    screen.pen = GRASS_FAR
    screen.rectangle(0, HY, SW, 4)
    screen.pen = GRASS
    screen.rectangle(0, HY + 4, SW, SH - HY - 4)

    t = TRACK
    n = t.n
    _frame[0] += 1
    frame = _frame[0]
    # ref: the player's track point
    dx = t.x[ref] - camx
    dz = t.z[ref] - camz
    near = _NEAR[ref] if _NEAR and dx * dx + dz * dz < NEAR_SLACK * NEAR_SLACK else _ALL
    tri = screen.triangle
    curv = t.curv
    for i in near:
        dx = t.x[i] - camx
        dz = t.z[i] - camz
        if dx * dx + dz * dz > FAR2:
            continue
        if dx * s + dz * c < -3.0:
            continue
        j = i + 1 if i + 1 < n else 0
        _cam_point(i, camx, camz, c, s, frame)
        _cam_point(j, camx, camz, c, s, frame)
        a = _PL[i]
        b = _PR[i]
        bb = _PR[j]
        aa = _PL[j]
        pen = ASPHALT_A if i & 1 else ASPHALT_B
        if a is not None and b is not None and bb is not None and aa is not None:
            screen.pen = pen     # past the near plane: no clipping
            tri(a, b, bb)
            tri(a, bb, aa)
        else:
            fill_ground([_CLX[i], _CRX[i], _CRX[j], _CLX[j]], [_CLZ[i], _CRZ[i], _CRZ[j], _CLZ[j]], pen)
        if KERBS and curv[i] > 0:
            pen = KERB_RED if i & 1 else KERB_WHITE
            k = _PKL[i]
            kk = _PKL[j]
            if a is not None and k is not None and kk is not None and aa is not None:
                screen.pen = pen
                tri(a, k, kk)
                tri(a, kk, aa)
            else:
                fill_ground([_CLX[i], _KLX[i], _KLX[j], _CLX[j]], [_CLZ[i], _KLZ[i], _KLZ[j], _CLZ[j]], pen)
            k = _PKR[i]
            kk = _PKR[j]
            if b is not None and k is not None and kk is not None and bb is not None:
                screen.pen = pen
                tri(b, k, kk)
                tri(b, kk, bb)
            else:
                fill_ground([_CRX[i], _KRX[i], _KRX[j], _CRX[j]], [_CRZ[i], _KRZ[i], _KRZ[j], _CRZ[j]], pen)

    for q in MARKS:
        dx = q[9] - camx
        dz = q[10] - camz
        if dx * dx + dz * dz > FAR2 or dx * s + dz * c < -3.0:
            continue
        draw_quad(q[0], q[1], q[2], q[3], q[4], q[5], q[6], q[7], camx, camz, c, s, q[8])


# ---------------------------------------------------------------------------
# Car meshes. Parts come from carmodel.py (or the box car): pivot in car
# space, steer factor, local verts, faces of [indices, nx, ny, nz, rgb, double].
# ---------------------------------------------------------------------------

# Fallback box car: (x, y, z centre, half w, h, l, steers, rgb)
BOXES = (
    (-0.125, 0.045, 0.140, 0.022, 0.045, 0.045, True, 0x28282E),
    (0.125, 0.045, 0.140, 0.022, 0.045, 0.045, True, 0x28282E),
    (0.000, 0.045, 0.010, 0.085, 0.020, 0.215, False, 0x464A52),
    (0.000, 0.095, 0.030, 0.075, 0.030, 0.160, False, 0x2864E6),
    (-0.130, 0.052, -0.130, 0.028, 0.052, 0.052, False, 0x28282E),
    (0.130, 0.052, -0.130, 0.028, 0.052, 0.052, False, 0x28282E),
    (0.000, 0.135, -0.175, 0.008, 0.025, 0.010, False, 0x787C82),
    (0.000, 0.163, -0.190, 0.115, 0.006, 0.040, False, 0xFAC828),
)

# Box corner i: bit0 = +x, bit1 = +y, bit2 = +z
BOX_FACES = (
    ((1, 3, 7, 5), 1, 0, 0),
    ((0, 4, 6, 2), -1, 0, 0),
    ((2, 6, 7, 3), 0, 1, 0),
    ((4, 5, 7, 6), 0, 0, 1),
    ((0, 2, 3, 1), 0, 0, -1),
)


def box_car():
    parts = []
    for bx, by, bz, hx, hy, hz, steers, rgb in BOXES:
        verts = []
        for i in range(8):
            verts.extend((hx if i & 1 else -hx, hy if i & 2 else -hy, hz if i & 4 else -hz))
        faces = [[list(idx), nx, ny, nz, carmodel.shade(rgb, nx, ny, nz), 0]
                 for idx, nx, ny, nz in BOX_FACES]
        parts.append({"pivot": [bx, by, bz], "steer": 1.0 if steers else 0.0,
                      "verts": verts, "faces": faces})
    return {"name": "Rotor RC", "parts": parts, "shadow": [-0.19, 0.19, -0.25, 0.25],
            "tune": {}, "faces": len(parts) * 5}


def _face_area(v, idx):
    p = [(v[3 * i], v[3 * i + 1], v[3 * i + 2]) for i in idx]
    if len(p) == 4:
        e1 = (p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2])
        e2 = (p[3][0] - p[1][0], p[3][1] - p[1][1], p[3][2] - p[1][2])
    else:
        e1 = (p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2])
        e2 = (p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2])
    x = e1[1] * e2[2] - e1[2] * e2[1]
    y = e1[2] * e2[0] - e1[0] * e2[2]
    z = e1[0] * e2[1] - e1[1] * e2[0]
    return math.sqrt(x * x + y * y + z * z) * 0.5


def _pen(pens, rgb):
    pen = pens.get(rgb)
    if pen is None:
        pen = color.rgb((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255)
        pens[rgb] = pen
    return pen


TWO_PI = 2 * math.pi
ORDER_ANGLES = 32    # headings with a precomputed face draw order


def _finish_mesh(raw_parts):
    """Runtime mesh (parts, orders, stamps) from (pivot, steer, verts, faces).

    Face: (a, b, c, d, nx, ny, nz, pen, double, w, pts, id); visible when
    n . cam > w. orders[b]: faces far to near for heading b. Depth uses
    camera-space z only (no pitch), so the order is distance-independent."""
    parts = []
    centres = []
    gid = 0
    for (px, py, pz), steer, verts, raw in raw_parts:
        n = len(verts)
        pts = [None] * n
        faces = []
        for a, b, c, d, nx, ny, nz, pen, double in raw:
            va = verts[a]
            f = (a, b, c, d, nx, ny, nz, pen, double,
                 nx * va[0] + ny * va[1] + nz * va[2], pts, gid)
            gid += 1
            faces.append(f)
            idx = (a, b, c) if d < 0 else (a, b, c, d)
            cx = sum(verts[i][0] for i in idx) / len(idx)
            cz = sum(verts[i][2] for i in idx) / len(idx)
            centres.append((f, px + cx, pz + cz))
        parts.append((px, py, pz, steer, verts, faces, pts, [0] * n))
    orders = []
    for b in range(ORDER_ANGLES):
        r = TWO_PI * b / ORDER_ANGLES
        cr = math.cos(r)
        sr = math.sin(r)
        keyed = []
        for f, x, z in centres:
            keyed.append((z * cr - x * sr, f[11], f))   # camera-space z
        keyed.sort(reverse=True)
        orders.append([e[2] for e in keyed])
    return (parts, orders, [0] * gid)


def _bounds(v):
    lo = [min(v[i] for i in range(k, len(v), 3)) for k in range(3)]
    hi = [max(v[i] for i in range(k, len(v), 3)) for k in range(3)]
    return lo, hi


def _is_wheel(pi, part):
    """Bounding box with two near-equal sides and one thinner (axle) side."""
    if pi == 0 or not part["verts"]:
        return False
    lo, hi = _bounds(part["verts"])
    d = sorted(hi[k] - lo[k] for k in range(3))
    return d[2] > 0 and d[1] > 0.8 * d[2] and d[0] < 0.85 * d[2]


def _wheel_proxy(part, pens, sides=6):
    """Wheel as a prism with `sides` sides, coloured from the area-weighted
    tread and side faces."""
    v = part["verts"]
    lo, hi = _bounds(v)
    dims = [hi[k] - lo[k] for k in range(3)]
    ax = dims.index(min(dims))                    # axle axis
    u, w = [k for k in range(3) if k != ax]
    c = [(lo[k] + hi[k]) / 2 for k in range(3)]
    rad = (dims[u] + dims[w]) / 4
    hw = dims[ax] / 2
    sums = ([0.0] * 4, [0.0] * 4)                 # tread, side: r, g, b, area
    for f in part["faces"]:
        acc = sums[1 if abs(f[1 + ax]) >= 0.5 else 0]
        area = _face_area(v, f[0])
        rgb = f[4]
        acc[0] += ((rgb >> 16) & 255) * area
        acc[1] += ((rgb >> 8) & 255) * area
        acc[2] += (rgb & 255) * area
        acc[3] += area
    rgbs = []
    for acc in sums:
        if acc[3] > 0:
            rgbs.append((int(acc[0] / acc[3]) << 16) | (int(acc[1] / acc[3]) << 8) | int(acc[2] / acc[3]))
        else:
            rgbs.append(rgbs[0] if rgbs else 0x28282E)
    t_rgb, s_rgb = rgbs
    s_rgb = ((((t_rgb >> 16) & 255) + ((s_rgb >> 16) & 255)) // 2 << 16
             | (((t_rgb >> 8) & 255) + ((s_rgb >> 8) & 255)) // 2 << 8
             | ((t_rgb & 255) + (s_rgb & 255)) // 2)     # side = mean(tread, side)
    tread = _pen(pens, t_rgb)
    side_pen = _pen(pens, s_rgb)
    verts = []
    for sgn in (-1, 1):
        for k in range(sides):
            t = TWO_PI * (k + 0.5) / sides
            q = [0.0, 0.0, 0.0]
            q[ax] = c[ax] + sgn * hw
            q[u] = c[u] + rad * math.cos(t)
            q[w] = c[w] + rad * math.sin(t)
            verts.append((q[0], q[1], q[2]))
    faces = []
    for k in range(sides):
        k1 = (k + 1) % sides
        t = TWO_PI * (k + 1) / sides
        n = [0.0, 0.0, 0.0]
        n[u] = math.cos(t)
        n[w] = math.sin(t)
        faces.append((k, k1, sides + k1, sides + k, n[0], n[1], n[2], tread, False))
    for sgn, off in ((-1, 0), (1, sides)):
        n = [0.0, 0.0, 0.0]
        n[ax] = float(sgn)
        for k in range(1, sides - 1, 2):           # cap as a quad fan
            d = off + k + 2 if k + 2 < sides else -1
            faces.append((off, off + k, off + k + 1, d, n[0], n[1], n[2], side_pen, False))
    return (part["pivot"], part["steer"], verts, faces)


def _part_faces(part, chosen, pens):
    """Raw part with only the chosen (area, part index, face) entries."""
    v = part["verts"]
    remap = {}
    verts = []
    faces = []
    for _, _, (idx, nx, ny, nz, rgb, double) in chosen:
        new = []
        for i in idx:
            if i not in remap:
                remap[i] = len(verts)
                verts.append((v[3 * i], v[3 * i + 1], v[3 * i + 2]))
            new.append(remap[i])
        d = new[3] if len(new) > 3 else -1
        faces.append((new[0], new[1], new[2], d, nx, ny, nz, _pen(pens, rgb), bool(double)))
    return (part["pivot"], part["steer"], verts, faces)


def build_mesh(model, pens):
    """Runtime mesh: body (part 0) with every face, wheels as prisms, other
    parts cut to their SMALL_PART_FACES largest faces."""
    raw = []
    for pi, part in enumerate(model["parts"]):
        if pi == 0:
            chosen = [(0.0, 0, f) for f in part["faces"]]
        elif _is_wheel(pi, part):
            raw.append(_wheel_proxy(part, pens))
            continue
        else:
            chosen = [(_face_area(part["verts"], f[0]), pi, f) for f in part["faces"]]
            chosen.sort(key=lambda e: e[0], reverse=True)
            chosen = chosen[:SMALL_PART_FACES]
        raw.append(_part_faces(part, chosen, pens))
    return _finish_mesh([m for m in raw if m[3]])


MESH = None          # set by use_model()
SHADOW_BOX = (-0.21, 0.21, -0.27, 0.27)
CAR_NAME = DEFAULT_CAR_NAME.upper()
status = ""
status_until = 0


def use_model(model):
    global MESH, SHADOW_BOX, CAR_NAME
    MESH = build_mesh(model, {})
    build_sprites(MESH)
    sx0, sx1, sz0, sz1 = model["shadow"]
    SHADOW_BOX = (sx0 - 0.02, sx1 + 0.02, sz0 - 0.02, sz1 + 0.02)
    CAR_NAME = str(model.get("name", DEFAULT_CAR_NAME)).upper()
    apply_tune(model.get("tune", {}))


def find_car_folder():
    # carmodel.py's folder, APP_DIR, root; in each, loose files and CAR_DIR
    bases = []
    mod = getattr(carmodel, "__file__", "")
    if "/" in mod:
        bases.append(_norm(mod.rsplit("/", 1)[0] or "/"))
    bases += [APP_DIR, "/"]
    sub = CAR_DIR.strip("/")
    if sub.startswith("./"):
        sub = sub[2:]
    subs = ("", sub) if CAR_FILES_LOOSE else (sub, "")
    tried = []
    for base in bases:
        for s in subs:
            folder = _join(base, s)
            if folder in tried:
                continue
            tried.append(folder)
            if carmodel.find_file(folder, "parameters.txt"):
                return folder, tried
    return None, tried


def load_car():
    global status, status_until
    folder, tried = find_car_folder()
    if folder:
        tag = folder.rstrip("/").rsplit("/", 1)[-1] or "root"
        cache = "%s/rotor-%s.json" % (CACHE_DIR, tag)
        try:
            model = carmodel.load_car(folder, cache)
            use_model(model)
            print("rotor: loaded %s from %s: %d of %d polys kept" % (
                model.get("name"), folder, model["faces"], model.get("polys", model["faces"])))
            return
        except Exception as e:  # keep racing with the box car
            sys.print_exception(e)
            status = "load failed: %s" % e
            status_until = badge.ticks + 15000
    else:
        print("rotor: no parameters.txt in any of", tried)
        status = "no car files found"
        status_until = badge.ticks + 6000
    use_model(box_car())


def draw_shadow(px, pz, cr, sr):
    x0, x1, z0, z1 = SHADOW_BOX
    xs = []
    zs = []
    for lx, lz in ((x0, z0), (x1, z0), (x1, z1), (x0, z1)):
        xs.append(px + lx * cr + lz * sr)
        zs.append(pz - lx * sr + lz * cr)
    fill_ground(xs, zs, SHADOW)


_mesh_frame = [0]


@micropython.native
def draw_mesh(mesh, wheel, px, pz, r, dst, ox, oy, cam_h):
    """Draw a car at camera-space (px, pz), yaw r, onto dst. (ox, oy): horizon
    centre on dst; cam_h: camera height."""
    parts, orders, fst = mesh
    cr = math.cos(r)
    sr = math.sin(r)
    _mesh_frame[0] += 1
    fr = _mesh_frame[0]
    for pvx, pvy, pvz, steer, verts, faces, pts, st in parts:
        if steer:
            a = r + wheel * steer
            ca = math.cos(a)
            sa = math.sin(a)
        else:
            ca = cr
            sa = sr
        bx = px + pvx * cr + pvz * sr
        bz = pz - pvx * sr + pvz * cr
        by = pvy - cam_h

        # camera in part space; back-face test is n . cam > w
        lx = bz * sa - bx * ca
        ly = -by
        lz = -bx * sa - bz * ca
        shown = False
        for f in faces:
            if f[8] or f[4] * lx + f[5] * ly + f[6] * lz > f[9]:
                fst[f[11]] = fr
                st[f[0]] = fr
                st[f[1]] = fr
                st[f[2]] = fr
                if f[3] >= 0:
                    st[f[3]] = fr
                shown = True
        if not shown:
            continue

        # project vertices of visible faces only
        i = 0
        for x, y, z in verts:
            if st[i] == fr:
                Z = bz - x * sa + z * ca
                if Z < 0.05:
                    Z = 0.05
                k = FOCAL / Z
                pts[i] = vec2(ox + (bx + x * ca + z * sa) * k, oy - (by + y) * k)
            i += 1

    # draw order for the car's yaw relative to the view ray
    n = len(orders)
    a = (r - math.atan2(px, pz)) % TWO_PI
    order = orders[int(a * n / TWO_PI + 0.5) % n]
    tri = dst.triangle
    last = None
    for f in order:
        if fst[f[11]] != fr:
            continue
        pen = f[7]
        if pen is not last:
            dst.pen = pen
            last = pen
        pts = f[10]
        p0 = pts[f[0]]
        p2 = pts[f[2]]
        tri(p0, pts[f[1]], p2)
        if f[3] >= 0:
            tri(p0, p2, pts[f[3]])


# ---------------------------------------------------------------------------
# CPU car sprites
# ---------------------------------------------------------------------------

SPRITE_BANDS = []    # (from distance, render distance, [(image, anchor x, anchor y)]), far first


def _render_set(mesh, boxes, z_ref, view):
    """SPRITE_ANGLES images of mesh at distance z_ref, camera elevation as
    seen from `view`. Returns [(image, anchor x, anchor y)] per heading,
    each image cropped to the projected bbox corners of its heading."""
    cam_h = CAM_H * z_ref / view
    out = []
    for b in range(SPRITE_ANGLES):
        r = TWO_PI * b / SPRITE_ANGLES
        cr = math.cos(r)
        sr = math.sin(r)
        x0 = y0 = 1e9
        x1 = y1 = -1e9
        for pvx, pvy, pvz, corners in boxes:
            bx = pvx * cr + pvz * sr
            bz = z_ref - pvx * sr + pvz * cr
            by = pvy - cam_h
            for x, y, z in corners:
                k = FOCAL / max(0.05, bz - x * sr + z * cr)
                sx = (bx + x * cr + z * sr) * k
                sy = -(by + y) * k
                x0 = min(x0, sx)
                x1 = max(x1, sx)
                y0 = min(y0, sy)
                y1 = max(y1, sy)
        ox = math.ceil(-x0) + 1
        oy = math.ceil(-y0) + 1
        img = image(int(math.ceil(x1 - x0)) + 3, int(math.ceil(y1 - y0)) + 3)
        try:
            img.antialias = image.X2
        except (AttributeError, TypeError):
            pass
        draw_mesh(mesh, 0.0, 0.0, z_ref, r, img, ox, oy, cam_h)
        out.append((img, ox, oy + cam_h * FOCAL / z_ref))
    return out


def build_sprites(mesh):
    """Render every SPRITE_SETS band."""
    global SPRITE_BANDS
    SPRITE_BANDS = []
    if not mesh[0] or SPRITE_ANGLES < 1:
        return
    boxes = []
    for pvx, pvy, pvz, steer, verts, faces, pts, st in mesh[0]:
        lo = [min(v[k] for v in verts) for k in range(3)]
        hi = [max(v[k] for v in verts) for k in range(3)]
        boxes.append((pvx, pvy, pvz, [(hi[0] if i & 1 else lo[0], hi[1] if i & 2 else lo[1],
                                        hi[2] if i & 4 else lo[2]) for i in range(8)]))
    size = 0
    for d0, z_ref, view in SPRITE_SETS:
        imgs = _render_set(mesh, boxes, z_ref, view)
        SPRITE_BANDS.append((d0, z_ref, imgs))
        size += sum(e[0].width * e[0].height * 4 for e in imgs)
        gc.collect()
    SPRITE_BANDS.sort(key=lambda e: e[0], reverse=True)
    try:
        free = gc.mem_free()
    except AttributeError:
        free = -1
    print("rotor: sprites %d KB, heap free %d KB" % (size // 1024, free // 1024))


def draw_sprite(X, Z, r):
    """Blit the sprite for yaw r relative to the view ray from the band for
    the car's distance. Scaled z_ref / Z, plus 1 / cos(view angle)
    horizontally for off-axis perspective; anchored at the ground point."""
    d = math.sqrt(X * X + Z * Z)
    for band in SPRITE_BANDS:
        if d >= band[0]:
            break
    a = (r - math.atan2(X, Z)) % TWO_PI
    img, ax, ay = band[2][int(a * (SPRITE_ANGLES / TWO_PI) + 0.5) % SPRITE_ANGLES]
    z_ref = band[1]
    sy = z_ref / Z
    sx = sy * d / Z
    k = FOCAL / Z
    screen.blit(img, rect(CX + X * k - ax * sx, HY + CAM_H * k - ay * sy,
                          img.width * sx, img.height * sy))


# ---------------------------------------------------------------------------
# Art: trackside banners, countdown digits, GitHub mark
# ---------------------------------------------------------------------------

def load_png(name):
    try:
        return image.load(app_path(name))
    except Exception:  # missing art is fine: banners fall back to text
        return None


GITHUB = load_png("github.png")
MONA = load_png("mona.png")


def text_image(text, fnt, pen, bg=None, pad=2):
    screen.font = fnt
    w, h = screen.measure_text(text)
    img = image(int(w) + pad * 2, int(h) + pad * 2)
    if bg is not None:
        img.pen = bg
        img.rectangle(0, 0, img.width, img.height)
    img.font = fnt
    img.pen = pen
    img.text(text, pad, pad)
    screen.font = font.sins
    return img


def banner(text, bg, fg, logo=None):
    screen.font = font.sins
    w, h = screen.measure_text(text)
    lw = logo.width + 3 if logo is not None else 0
    img = image(int(w) + lw + 6, 16)
    img.pen = bg
    img.rectangle(0, 0, img.width, img.height)
    if logo is not None:
        img.blit(logo, vec2(3, (16 - logo.height) // 2))
    img.font = font.sins
    img.pen = fg
    img.text(text, 3 + lw, (16 - h) // 2)
    return img


def mona_board():
    img = image(30, 30)
    img.pen = color.rgb(255, 255, 255)
    img.rectangle(0, 0, 30, 30)
    if MONA is not None:
        img.blit(MONA, vec2(3, 3))
    return img


WHITE = color.rgb(255, 255, 255)
DARK = color.rgb(13, 17, 23)
BLACK = color.rgb(0, 0, 0)
LIGHT_MARK = load_png("github-light.png")   # same mark, light, for dark banners

BANNERS = {
    "universe": banner("UNIVERSE 2026", DARK, ACCENT, LIGHT_MARK),
    "github": banner("GitHub", WHITE, DARK, GITHUB),
    "rotor": banner("ROTOR", DARK, ACCENT_2, LIGHT_MARK),
    "start": banner("START", DARK, WHITE),
    "finish": banner("FINISH", WHITE, DARK),
    "mona": mona_board(),
}

# (distance along the track, side: +1 right / -1 left, banner, width m, height m)
SIGNS = (
    (6.0, -1, "universe", 1.6, 0.30),
    (19.0, -1, "github", 1.2, 0.30),
    (24.0, 1, "mona", 0.6, 0.60),
    (40.0, -1, "rotor", 1.2, 0.30),
    (52.0, 1, "universe", 1.6, 0.30),
    (62.0, -1, "mona", 0.6, 0.60),
    (78.0, 1, "github", 1.2, 0.30),
    (96.0, -1, "universe", 1.6, 0.30),
    (112.0, 1, "rotor", 1.2, 0.30),
    (126.0, -1, "mona", 0.6, 0.60),
    (140.0, -1, "github", 1.2, 0.30),
    (TRACK.length - 0.3, 1, "start", 0.9, 0.25),
    (TRACK.finish - 0.3, -1, "finish", 0.9, 0.25),
)
SIGN_LIFT = 0.18     # gap under the banner, m


def place_signs():
    out = []
    for d, side, key, w, h in SIGNS:
        i = TRACK.point_at(d)
        lat = side * (TRACK.half[i] + trackmod.KERB + 0.55)
        x, z, _ = TRACK.pose_at(d, lat)
        out.append((x, z, BANNERS[key], w, h))
    return out


def draw_sign(sign, X, Z):
    x, z, img, w, h = sign
    k = FOCAL / Z
    sw = w * k
    if sw < 3:
        return
    sh = h * k
    sx = CX + X * k - sw / 2
    y_ground = HY + CAM_H * k
    y_bottom = HY - (SIGN_LIFT - CAM_H) * k
    screen.pen = POST
    screen.line(sx + sw * 0.1, y_bottom, sx + sw * 0.1, y_ground)
    screen.line(sx + sw * 0.9, y_bottom, sx + sw * 0.9, y_ground)
    screen.blit(img, rect(sx, y_bottom - sh, sw, sh))


COUNT_IMAGES = (
    text_image("GO!", font.ziplock, ACCENT),
    text_image("1", font.ziplock, color.rgb(255, 220, 90)),
    text_image("2", font.ziplock, color.rgb(255, 166, 87)),
    text_image("3", font.ziplock, color.rgb(255, 110, 100)),
)
TAG_IMAGE = text_image("CPU", font.sins, WHITE, None, 1)


def tag_image(pen):
    """CPU tag: label on a rounded rect in pen."""
    w = TAG_IMAGE.width
    h = TAG_IMAGE.height
    img = image(w + 4, h + 1)
    try:
        img.antialias = image.X2
    except (AttributeError, TypeError):
        pass
    img.pen = pen
    img.shape(shape.rounded_rectangle(0, 0, w + 4, h + 1, 3))
    img.blit(TAG_IMAGE, vec2(2, 1))
    return img


def make_minimap(size=34):
    t = TRACK
    mnx = min(t.x)
    mxx = max(t.x)
    mnz = min(t.z)
    mxz = max(t.z)
    scale = (size - 4) / max(mxx - mnx, mxz - mnz)
    img = image(size, size)
    img.pen = color.rgb(13, 17, 23, 150)
    img.shape(shape.rounded_rectangle(0, 0, size, size, 4))
    img.pen = color.rgb(200, 210, 220)
    ox = (size - (mxx - mnx) * scale) / 2
    oz = (size - (mxz - mnz) * scale) / 2

    def m(x, z):
        return ox + (x - mnx) * scale, size - (oz + (z - mnz) * scale)

    for i in range(t.n):
        j = (i + 1) % t.n
        x0, y0 = m(t.x[i], t.z[i])
        x1, y1 = m(t.x[j], t.z[j])
        img.line(x0, y0, x1, y1)
    return img, m


# ---------------------------------------------------------------------------
# Race
# ---------------------------------------------------------------------------

COUNTDOWN_MS = 3000
GO_MS = 900

player = Car("YOU", False, None)
cars = [player]
for _n in range(CPU_COUNT):
    cars.append(Car("CPU %d" % (_n + 1), True, TAG_PENS[_n % len(TAG_PENS)]))

phase = "load"       # load -> intro -> start -> countdown -> race -> done
intro_slide = 0
phase_t = 0          # ms at phase start
race_ms = 0
cam_yaw = 0.0
orbit = 0.0
BEST_KEY = "best_ms_%d" % LAPS
best = {BEST_KEY: 0}
new_best = False
MARKS = []
SIGNS_PLACED = []
MINIMAP = None
MINIMAP_MAP = None


def load_best():
    if State is None:
        return
    try:
        State.load("rotor", best)
    except Exception:
        pass


def save_best():
    if State is None:
        return
    try:
        State.save("rotor", best)
    except Exception:
        pass


def setup_grid():
    global race_ms, cam_yaw, new_best
    slots = list(range(CPU_COUNT + 1))
    slots.remove(PLAYER_SLOT)
    for car in cars:
        slot = PLAYER_SLOT if car is player else slots.pop(0)
        d, lat = grid_pos(slot)
        car.place(d, lat)
        if car.cpu:
            car.top_scale = rand(0.80, 0.94)
            car.acc_scale = rand(0.85, 1.0)
            car.lane = lat / 1.3
            car.lane_target = car.lane
    cam_yaw = player.yaw
    race_ms = 0
    new_best = False


def go_to_start():
    """Back to the "Press B to start" screen with a fresh grid."""
    global phase, phase_t
    setup_grid()
    phase = "start"
    phase_t = badge.ticks


def start_countdown():
    global phase, phase_t
    phase = "countdown"
    phase_t = badge.ticks


def standings():
    def key(c):
        if c.done:
            return (0, c.time, 0)
        return (1, 0, -c.dist)
    return sorted(cars, key=key)


def fmt_time(ms):
    if ms is None:
        return "--:--.--"
    s = ms / 1000
    m = int(s // 60)
    return "%d:%05.2f" % (m, s - m * 60)


def finish_car(car):
    global phase, phase_t, new_best
    car.done = True
    car.time = race_ms
    if car is player:
        car.brake = True
        phase = "done"
        phase_t = badge.ticks
        if best[BEST_KEY] == 0 or race_ms < best[BEST_KEY]:
            best[BEST_KEY] = race_ms
            new_best = True
            save_best()


def step_race(dt):
    global race_ms
    racing = phase in ("race", "done")
    if racing:
        race_ms += int(dt * 1000)   # keeps running so later CPUs get a time
    for car in cars:
        if car.cpu:
            if racing and not car.done:
                throttle, steer = cpu_drive(car, dt)
            else:
                throttle, steer = 0, 0
                car.brake = car.done
        elif phase == "race":
            throttle = 0
            if held(BTN_UP):
                throttle += 1
            if held(BTN_DOWN):
                throttle -= 1
            steer = 0
            if held(BTN_C):
                steer += 1
            if held(BTN_A):
                steer -= 1
        else:
            throttle, steer = 0, 0
        car.update(dt, throttle, steer)
    bump_cars(cars)
    for car in cars:
        track_car(car)
        if racing and not car.done:
            n = laps_done(car)
            if n > car.laps_done:
                lap = race_ms - car.lap_start
                if car.best_lap is None or lap < car.best_lap:
                    car.best_lap = lap
                car.laps_done = n
                car.lap_start = race_ms
        if racing and not car.done and car.dist >= RACE_DIST:
            if car.cpu or phase == "race":
                finish_car(car)


# ---------------------------------------------------------------------------
# Drawing the world and HUD
# ---------------------------------------------------------------------------

def draw_world(camx, camz, cyaw):
    c = math.cos(cyaw)
    s = math.sin(cyaw)
    screen.antialias = image.OFF
    draw_ground(camx, camz, c, s, player.idx)

    items = []
    for car in cars:
        px, pz = to_cam(car.x, car.z, camx, camz, c, s)
        if pz < 0.5 or px * px + pz * pz > FAR2:
            continue  # beside/behind the camera, or too far
        items.append((pz, 0, car, px))
    for sign in SIGNS_PLACED:
        X, Z = to_cam(sign[0], sign[1], camx, camz, c, s)
        if Z < 0.5 or Z > FAR:
            continue
        items.append((Z, 1, sign, X))
    items.sort(key=lambda it: it[0], reverse=True)

    tags = []
    for Z, kind, obj, X in items:
        if kind == 1:
            draw_sign(obj, X, Z)
            continue
        car = obj
        r = car.yaw - cyaw
        screen.antialias = image.OFF
        draw_shadow(X, Z, math.cos(r), math.sin(r))
        if car.cpu and SPRITE_BANDS:
            draw_sprite(X, Z, r)
        else:
            screen.antialias = image.X2
            draw_mesh(MESH, car.wheel, X, Z, r, screen, CX, HY, CAM_H)
        if car.cpu and Z < 9.0:
            tags.append((car, X, Z))

    screen.antialias = image.X2
    for car, X, Z in tags:
        k = FOCAL / Z
        img = car.tag_img
        if img is None:
            continue
        screen.blit(img, vec2(CX + X * k - img.width / 2, HY - (0.30 - CAM_H) * k - img.height))


def centred(text, y, pen, fnt=None, x0=0, width=None):
    if fnt is not None:
        screen.font = fnt
    w, _ = screen.measure_text(text)
    screen.pen = pen
    screen.text(text, x0 + ((SW if width is None else width) - w) / 2, y)
    screen.font = font.sins


def draw_minimap():
    if MINIMAP is None:
        return
    mx = SW - MINIMAP.width - 2
    my = SH - MINIMAP.height - 2
    screen.blit(MINIMAP, vec2(mx, my))
    for car in cars:
        x, y = MINIMAP_MAP(car.x, car.z)
        screen.pen = ACCENT if car is player else car.tag_pen
        r = 2 if car is player else 1.5
        screen.shape(shape.circle(mx + x, my + y, r))


def draw_hud(ms_now):
    order = standings()
    pos = order.index(player) + 1
    screen.font = font.sins
    screen.pen = HUD
    screen.text("LAP %d/%d" % (lap_of(player), LAPS), 3, 2)
    screen.pen = HUD_DIM
    screen.text("BEST " + fmt_time(player.best_lap), 3, 14)
    screen.font = font.nope
    screen.pen = HUD
    screen.text("P%d/%d" % (pos, len(cars)), 3, SH - 26)
    t = fmt_time(player.time if player.done else race_ms)
    w, _ = screen.measure_text(t)
    screen.text(t, (SW - w) / 2, 1)
    if LIGHT_MARK is not None:
        screen.blit(LIGHT_MARK, vec2(SW - LIGHT_MARK.width - 3, 1))
    screen.font = font.sins
    mph = int(abs(player.vf) / SIM_PER_MPH + 0.5)
    screen.pen = HUD
    screen.text("%d MPH" % mph, 3, SH - 13)

    warn = None
    if phase == "race":
        i = player.idx
        heading = math.sin(player.yaw) * TRACK.dx[i] + math.cos(player.yaw) * TRACK.dz[i]
        if heading < -0.5 and abs(player.vf) > 0.8:
            warn = "WRONG WAY"
        elif player.off:
            warn = "OFF TRACK"
    if status and ms_now < status_until:
        warn = status
    if warn:
        screen.pen = HUD_WARN
        msg = warn
        while len(msg) > 4 and screen.measure_text(msg)[0] > SW - 50:
            msg = msg[:-1]
        w, _ = screen.measure_text(msg)
        screen.text(msg, (SW - w) / 2, SH - 26)
    draw_minimap()


def draw_countdown(ms_now):
    el = ms_now - phase_t
    if phase == "countdown":
        idx = 3 - el // 1000          # 3, 2, 1
        frac = (el % 1000) / 1000
    else:
        idx = 0                       # GO!
        frac = el / GO_MS
    img = COUNT_IMAGES[max(0, min(3, idx))]
    scale = 2.2 - 0.6 * frac
    w = img.width * scale
    h = img.height * scale
    screen.blit(img, rect((SW - w) / 2, 42 - h / 2, w, h))
    if phase == "countdown":
        y = SH - 44
        x0 = 3
        w = SW - 42           # stops short of the minimap
        screen.pen = PANEL
        screen.shape(shape.rounded_rectangle(x0, y, w, 27, 5))
        centred("ROTOR", y + 1, ACCENT_2, font.nope, x0, w)
        centred("GitHub Universe 2026", y + 13, ACCENT, None, x0, w)


def draw_results(ms_now):
    order = standings()
    x0 = 14
    y0 = 6
    w = SW - 28
    h = SH - 12
    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(x0, y0, w, h, 6))
    if LIGHT_MARK is not None:
        screen.blit(LIGHT_MARK, vec2(x0 + 4, y0 + 3))
    centred("RESULTS", y0 + 2, ACCENT, font.nope)
    screen.font = font.sins
    y = y0 + 17
    for i, car in enumerate(order):
        mine = car is player
        if mine:
            screen.pen = color.rgb(126, 231, 135, 60)
            screen.rectangle(x0 + 3, y, w - 6, 11)
        screen.pen = ACCENT if mine else HUD
        screen.text("%d" % (i + 1), x0 + 6, y - 1)
        if car.cpu:
            screen.pen = car.tag_pen
            screen.shape(shape.circle(x0 + 20, y + 5, 2))
            screen.pen = HUD
        screen.text(car.name, x0 + 26, y - 1)
        t = fmt_time(car.time)
        tw, _ = screen.measure_text(t)
        screen.pen = (ACCENT if mine else HUD) if car.done else HUD_DIM
        screen.text(t, x0 + w - tw - 6, y - 1)
        y += 11
    y += 1
    screen.pen = PANEL_EDGE
    screen.line(x0 + 6, y, x0 + w - 6, y)
    if best[BEST_KEY]:
        label = ("NEW BEST " if new_best else "BEST ") + fmt_time(best[BEST_KEY])
        centred(label, y + 1, ACCENT_2 if new_best else HUD_DIM)
    if (ms_now // 500) % 2 == 0:
        centred("Press B to restart", y0 + h - 13, HUD)


def draw_loading():
    screen.pen = BLACK
    screen.rectangle(0, 0, SW, SH)
    centred("Loading...", SH / 2 - 6, HUD_DIM)


_fps = [0.0]


def draw_fps(dt_ms):
    if dt_ms > 0:
        _fps[0] += (1000.0 / dt_ms - _fps[0]) * 0.1    # EMA, ~10 frames
    screen.font = font.sins
    screen.pen = HUD
    t = "%d FPS" % int(_fps[0] + 0.5)
    w, _ = screen.measure_text(t)
    screen.text(t, SW - w - 3, 14)


def fade(alpha):
    """Darken the whole screen; 255 is fully black."""
    if alpha <= 0:
        return
    screen.pen = color.rgb(0, 0, 0, min(255, int(alpha)))
    screen.rectangle(0, 0, SW, SH)


def slide_title():
    centred("ROTOR", 14, ACCENT_2, font.ziplock)
    centred("RC Car Simulator", 40, HUD_DIM)
    centred("by Team 1", 60, ACCENT, font.nope)
    centred("BGM  redhatgamer  Priya", 78, HUD)


def slide_universe():
    if LIGHT_MARK is not None:
        w = LIGHT_MARK.width * 2
        screen.blit(LIGHT_MARK, rect((SW - w) / 2, 20, w, LIGHT_MARK.height * 2))
    centred("Created for", 62, HUD_DIM)
    centred("GitHub Universe 2026", 76, ACCENT, font.nope)


def slide_thanks():
    centred("Special thanks to:", 10, ACCENT_2, font.nope)
    centred("Henrique G. Britos", 32, HUD, font.nope)
    centred("(Car Model)", 46, HUD_DIM)
    centred("PJ Metz", 66, HUD, font.nope)
    centred("(GCE Program Manager)", 80, HUD_DIM)


SLIDES = (slide_title, slide_thanks, slide_universe)


def draw_intro(ms_now):
    """Draw the current intro slide with its fade. Returns False when done."""
    global intro_slide, phase_t
    while True:
        hold = SLIDE_HOLD_MS[intro_slide]
        el = ms_now - phase_t
        if el < FADE_MS * 2 + hold:
            break
        intro_slide += 1
        phase_t += FADE_MS * 2 + hold
        if intro_slide >= len(SLIDES):
            return False
    screen.pen = DARK
    screen.rectangle(0, 0, SW, SH)
    SLIDES[intro_slide]()
    if el < FADE_MS:
        fade(255 * (1 - el / FADE_MS))
    elif el > FADE_MS + hold:
        fade(255 * (el - FADE_MS - hold) / FADE_MS)
    return True


def draw_start(ms_now):
    x0 = 12
    w = SW - 24
    y = 22
    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(x0, y, w, 62, 6))
    if LIGHT_MARK is not None:
        screen.blit(LIGHT_MARK, vec2(x0 + 4, y + 4))
    centred("ROTOR", y + 3, ACCENT_2, font.ziplock)
    centred("GitHub Universe 2026", y + 26, ACCENT)
    if best[BEST_KEY]:
        centred("BEST " + fmt_time(best[BEST_KEY]), y + 37, HUD_DIM)
    elif LAPS > 1:
        centred("%d LAPS" % LAPS, y + 37, HUD_DIM)
    if (ms_now // 500) % 2 == 0:
        centred("Press B to start", y + 49, HUD)
    el = ms_now - phase_t
    if el < FADE_MS:
        fade(255 * (1 - el / FADE_MS))


# ---------------------------------------------------------------------------

def update():
    global phase, phase_t, cam_yaw, orbit, MARKS, SIGNS_PLACED, MINIMAP, MINIMAP_MAP, _NEAR

    if phase == "load":
        draw_loading()
        phase = "load2"
        return
    if phase == "load2":
        draw_loading()
        random.seed(badge.ticks)
        load_car()
        gc.collect()
        MARKS = make_marks()
        _NEAR = _near_lists()
        SIGNS_PLACED = place_signs()
        MINIMAP, MINIMAP_MAP = make_minimap()
        load_best()
        setup_grid()
        phase = "intro"
        phase_t = badge.ticks
        return

    now = badge.ticks
    dt_ms = badge.ticks_delta
    dt = dt_ms / 1000
    if dt > 0.05:
        dt = 0.05

    # B: start the race from the start screen; anywhere else, back to it
    if pressed(BTN_B):
        if phase == "start":
            start_countdown()
        else:
            go_to_start()
        now = badge.ticks

    if phase == "intro":
        if draw_intro(now):
            if SHOW_FPS:
                draw_fps(dt_ms)
            return
        go_to_start()
        now = badge.ticks

    if phase == "countdown" and now - phase_t >= COUNTDOWN_MS:
        phase = "race"
        phase_t = now

    step_race(dt)

    if phase in ("done", "start"):
        orbit += ORBIT_SPEED * dt
        camx = player.x + math.sin(orbit) * ORBIT_R
        camz = player.z + math.cos(orbit) * ORBIT_R
        cyaw = math.atan2(player.x - camx, player.z - camz)
        if phase == "start":
            cam_yaw = player.yaw   # the countdown starts from the chase view
    else:
        cam_yaw += (player.yaw - cam_yaw) * min(1.0, CAM_FOLLOW * dt)
        cyaw = cam_yaw
        camx = player.x - math.sin(cyaw) * CAM_DIST
        camz = player.z - math.cos(cyaw) * CAM_DIST
        orbit = cyaw + math.pi

    draw_world(camx, camz, cyaw)

    if phase == "done":
        draw_results(now)
    elif phase == "start":
        draw_start(now)
    else:
        draw_hud(now)
        if phase == "countdown" or (phase == "race" and now - phase_t < GO_MS):
            draw_countdown(now)
    if SHOW_FPS:
        draw_fps(dt_ms)


run(update)
