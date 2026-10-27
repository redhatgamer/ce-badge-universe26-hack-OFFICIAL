# Mona Launch handoff

This note preserves the app's design, the physical debugging results, and
important limits for future Copilots. It describes one tested badge build; it
is not a guarantee for every Tufty or Universe badge firmware.
This is an owner-managed demo, not a TeamN submission.

## App

Mona Launch uses a held, controlled upward flick to launch Mona, shows her
flight and peak height, and saves the best score. The detector projects the
motion onto the current gravity baseline so sideways and downward impulses do
not launch her. A separate button press is available as a test fallback. The
app waits for the title-screen button to be released before accepting a flick
or test press, so one press cannot open READY and launch Mona at the same time.

The app needs:

- `__init__.py` for the game.
- `icon.png`, a 24x24 app icon.
- `mona.png`, a 168x48 PNG sprite sheet with 7 columns and 2 rows.

The empty `assets/` directory from the source app was not copied.

The app first uses the executing file's directory when available, otherwise
the launcher's current working directory (including `/` for web-editor runs).
If that directory is unavailable, it checks `/remote/apps/mona-launch`,
`/system/apps/mona-launch`, `/apps/mona-launch`, `/mona-launch`, and `/` in
that order. This avoids selecting another installed app with the same name.
It uses `os.stat()` instead of `os.path`, which is not available on the tested
Tufty MicroPython build.

## Physical test record

The connected device reported:

```text
MicroPython bw-1.28.0-3
Pimoroni Tufty 2350 with RP2350
```

The user confirmed that the title and READY screens appeared, ordinary
handling did not launch Mona after the button-release change and 0.5g motion
threshold, and a controlled flick did launch her. Earlier testing displayed
the result screen. High-score persistence was not separately retested after
the final motion-threshold change.

The 0.5g threshold is an app setting that passed this one physical test. Do
not copy it as a universal sensor threshold. One stationary sensor reading
was `(403, -1194, -15905, 80, -362, 164)`; no usable motion sample was
captured, so this is not a full sensor calibration.

## Device-specific API findings

The tested firmware exposed this sprite path:

```python
sheet = image.load(path).spritesheet(columns, rows)
sprite = sheet.sprite(index)
```

On that build, `SpriteSheet` was not importable from `badgeware`, the
`spritesheet` object had no `.animation()` method, and `run()` rejected an
`init=` argument. `shape.line(x1, y1, x2, y2, width)` required the width
argument; all five app line calls now pass `1`. The app uses module-level
`run(update)`.

These observations apply to the queried build only. Query the connected
device before reusing them on another firmware version.

## Debugging history

The first sprite code called `.animation()` on the object returned by
`image.load(...).spritesheet(...)`. The badge reported that the object had no
`animation` attribute. Importing `SpriteSheet` from `badgeware` was then
tried, but the tested firmware did not provide that name. The verified fix
was to keep `image.load(...).spritesheet(...)` and load the needed frames with
`.sprite(index)`.

The next startup attempt passed `init=` to `run()` and failed with:

```text
TypeError: unexpected keyword argument 'init'
```

The app now loads saved state before calling `run(update)`.

The first draw attempt then failed with `TypeError: missing required
positional arguments` at a `shape.line(...)` call. The badge accepted
`shape.line(0, 0, 10, 10, 1)`. Adding a width to every line call fixed the
screen drawing error.

The transferred app later failed at startup because it used
`os.path.dirname(__file__)`. The tested Tufty MicroPython build has `os` but
does not provide desktop Python's `os.path`. The app now finds its directory
with `os.stat()` and loads `mona.png` relative to that directory.

After the title screen worked, pressing A could carry from the title into
launch. The READY state now waits for the start button to be released and
resets the motion baseline before it accepts another action.

Ordinary handling then triggered the original 0.18g, largest-axis detector.
The first transferred version used a directionless 0.5g three-axis magnitude.
The app now requires a 0.5g signed impulse in the upward direction relative to
the gravity baseline, rejecting opposite and lateral movement. The signed
detector and the HIRES-scaled layout still require a new physical check.

## Serial and deployment cautions

- Read `hardware/USB_SERIAL.md` before connecting to another badge. Discover
  its current serial port; do not reuse a host-assigned port name.
- Serial access interrupted the running app during this session. One attempted
  sensor-capture command did not return data and left the display on its last
  frame; RESET restored the menu. Confirm a REPL command has completed before
  asking someone to perform a physical movement test.
- Only one program can own the serial port. Do not run multiple serial
  clients at once.
- The connected badge appeared in Finder as `TUFTY` with apps under `apps/`.
  The repository deployment tool and guide expect `BADGER/system/apps`.
  Check the actual mounted layout before using a deployment script.
- The local simulator was not available in the source checkout because
  Pygame was missing. Use the official repo's web simulator for UI paths, but
  test IMU behavior on the physical badge.

## Source and changes

The app came from `badge/apps/mona-launch/` on the
`feature/mona-launch` branch in `ce-badge-hack-universe26`. Keep that source
copy until the destination pull request is reviewed. The transferred app
passed the hardware-target app validator with no warnings, and its PNG assets
match the source files. The destination uses an app-relative asset path so it
can run from this folder as well as after deployment.
