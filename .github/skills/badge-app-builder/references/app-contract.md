# Universe 2026 app contract

## Directory

Campus Experts build in their assigned team folder:

```text
TeamN/<app-name>/
├── __init__.py
├── icon.png
└── assets/
```

An app is discovered when it contains `__init__.py` or `__init__.mpy`.
Provide a 24x24 `icon.png`. The `assets/` directory is optional.

## Runtime

The launcher supplies common globals such as `badge`, `screen`, `image`,
`font`, `color`, `shape`, `brush`, `vec2`, `rect`, `mat3`, `run`, button
constants, display-mode constants, and filesystem helpers.

Use an explicit app directory when an app has local modules or relative
assets. The same source must work in the simulator, from a temporary remote
mount, and after a manual copy to either supported badge filesystem layout.
The tested Tufty MicroPython build does not provide desktop Python's
`os.path`, so do not use `os.path.dirname(__file__)` or `os.path.join()`.
Prefer the executing file's directory when `__file__` includes a path;
otherwise preserve the launcher's current working directory (including `/`
for web-editor runs). Only then try fixed locations, so a same-named built-in
app cannot take precedence over the running app's modules and assets.

```python
import os
import sys

APP_DIR = os.getcwd()
APP_FILE = globals().get("__file__", "")
if "/" in APP_FILE:
    APP_DIR = APP_FILE.rsplit("/", 1)[0] or "/"
    if not APP_DIR.startswith("/"):
        APP_DIR = os.getcwd().rstrip("/") + "/" + APP_DIR

APP_DIRS = (
    APP_DIR,
    "/remote/apps/my_app",
    "/system/apps/my_app",
    "/apps/my_app",
    "/my_app",
    "/",
)
for app_dir in APP_DIRS:
    try:
        os.stat(app_dir)
        APP_DIR = app_dir
        break
    except OSError:
        pass

os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)
```

After changing directory, load app-owned assets with relative paths such as
`image.load("assets/player.png")`. Keep the path list short and use this shared
pattern instead of adding simulator-only or badge-only branches throughout the
app.

The minimal lifecycle is:

```python
def update():
    pass


run(update)
```

An app may return a `/system/apps/<name>` path from `update()` when it acts as a
launcher. Ordinary apps return `None`.

## Input and timing

```python
if badge.pressed(BUTTON_SELECT):
    confirm()

if badge.held(BUTTON_LEFT):
    x -= speed * (badge.ticks_delta / 1000)

if badge.released(BUTTON_BACK):
    cancel()
```

Use logical actions. HOME is reserved for returning to the launcher.

## Drawing and assets

Set `screen.pen` before drawing and use `screen.shape(...)`, `screen.blit(...)`,
and `screen.text(...)`. Use `image.load(...)` for images and
`image.load(...).spritesheet(columns, rows)` for sprite sheets. Prefer
paletted/optimized PNGs and load large assets on demand.

## State

```python
from badgeware import State

state = {"score": 0}
State.load("my_app", state)
State.save("my_app", state)
```

Save after meaningful changes, not on every frame. Never store credentials in
app state.
