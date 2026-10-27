# Universe 2026 emulator workflow

Use the [Pimoroni Badgeware Web Simulator](https://pimoroni.github.io/badgeware-web-simulator/)
for a quick visual check of an app. It runs in a browser with no install and
models the upstream Tufty 2350 Badgeware runtime for UI and state iteration.
Custom Universe 2026 hardware and firmware APIs still require physical testing;
it does not prove physical touch, IMU, wireless, GPIO, IR, power, or exact MicroPython memory behavior.

## Setup

No local install is required. Open
https://pimoroni.github.io/badgeware-web-simulator/ (or https://try.badgewa.re),
copy the app's `__init__.py` and local modules into the editor, upload binary
assets with the Files panel, and press F5 or **Run**.

Use the app-directory pattern in [app-contract.md](app-contract.md). It prefers
the executing file's directory or the current working directory (`/` for
editor runs) before checking `/remote/apps/<name>` and physical badge
locations, so a same-named built-in app cannot override uploaded assets.
It does not use unsupported desktop-only `os.path` helpers. After the
app changes into its directory, use relative paths for local modules and
assets.

If you want offline or command-line testing instead, see
[`pimoroni/badgeware-simulator`](https://github.com/pimoroni/badgeware-simulator),
a native simulator Pimoroni builds directly on the real PicoVector graphics
library.

## Controls

Click the 3D badge once to give it keyboard focus, then use:

- Left arrow: A.
- Space: B.
- Right arrow: C.
- Up/Down arrows: Up/Down.
- Esc: Home (badgeOS menu).
- F5 or Run: run the code in the editor.

These are the simulator's own documented controls (https://try.badgewa.re)
and may change as Pimoroni updates it.

## What to test

Exercise every screen, logical control, launcher return path, first-run state
path, saved-state path, and error path.

Do not mark BLE, touch, IMU, GPIO, IR, battery, charging, wireless, or exact
memory behavior as complete from simulator success alone.
