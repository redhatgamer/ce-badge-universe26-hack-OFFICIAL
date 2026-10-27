---
name: badge-app-builder
description: Build, debug, validate, emulate, and deploy MicroPython apps for the GitHub Hackable Conference Badge. Use when someone has an app idea, edits TeamN apps or badge/apps examples, asks about Badgeware, runs the badge simulator, or wants to test on a physical BADGER device.
compatibility: Requires Python 3.10+ for bundled tools (standard library only). Emulator use requires a browser and no local install. Physical deployment requires a mounted BADGER or TUFTY USB volume. Advanced API verification may require GitHub access.
license: MIT
metadata:
  summary: Turn an idea into a validated badge app for the emulator and physical hardware.
  status: active
---

# Badge App Builder

Help the user turn an idea into a badge app that works within the physical badge's constraints. Treat the physical badge as the compatibility target and the emulator as a fast development aid.

## Start with the repository

1. Read the relevant existing app before writing code. Use [references/examples.md](references/examples.md) to pick the closest examples.
2. Read [references/hardware.md](references/hardware.md) and [references/app-contract.md](references/app-contract.md) before creating or restructuring an app.
3. Read only the API sections needed from [references/badgeware-api.md](references/badgeware-api.md). The filename is retained for compatibility, but the reference describes the active 2026 runtime.
4. For emulator work, read [references/emulator.md](references/emulator.md). For device work, read [references/physical-badge.md](references/physical-badge.md).
   For a quick browser preview, use the Pimoroni Badgeware Web Simulator:
   https://pimoroni.github.io/badgeware-web-simulator/
5. Prefer the checked-out repository implementation over prose when they disagree.
6. For an advanced, missing, or potentially changed API, verify it against the
   Universe 2026 `badge/` tree and hardware references in `badger/home`.
7. Treat `badge25/` as the archived Universe 2025 runtime. Do not use its
   old drawing and input APIs for new apps.
8. For a physical-device error, read `hardware/USB_SERIAL.md`, query the
   connected firmware, and capture the exact traceback before changing code.
   Verify names and call signatures against that build; the Tufty product name
   alone does not identify its API. Serial access can interrupt the running
   app, so use one serial client and confirm a command completed before asking
   for a physical test.

## Turn an idea into a badge design

Before implementation, reduce the idea to:

- The primary screen or state machine.
- A control map using logical actions such as UP, DOWN, LEFT, RIGHT, SELECT,
  BACK, MENU, and HOME. HOME is reserved for returning to the launcher.
- Required assets, persistent state, networking, Bluetooth, IR, LEDs, or expansion hardware.
- What the emulator can prove and what must be tested on a physical badge.
- A memory and performance approach suitable for the RP2350B, 8 MB PSRAM,
  16 MB flash, and the default 160x120 logical framebuffer.

Make reasonable product decisions when the request is open-ended. Ask only when a wrong assumption would waste substantial work or require unavailable hardware.

## Build or modify the app

In this Campus Experts repository, create submissions under the assigned
`TeamN/<app-name>/` folder. Treat `badge/apps/` as read-only examples and shared
badge code unless the user explicitly asks to maintain them. A repo owner may
request a demo outside the team-submission workflow; use the requested demo
folder and do not label it as a TeamN submission. For a new Team 1 app, run:

```bash
python3 .github/skills/badge-app-builder/scripts/scaffold_app.py <app-name> \
  --title "App Title" --apps-dir Team1
```

Then:

1. Keep `update()` non-blocking and efficient; use `badge.ticks` or
   `badge.ticks_delta` for timing.
2. Put initialization in `init()` and state/resource cleanup in `on_exit()` when needed.
3. Use the shared app-directory pattern from
   [references/app-contract.md](references/app-contract.md), then use relative
   paths for app-owned assets. Do not use `os.path`; it is absent on the tested
   badge MicroPython runtime.
4. Use the 2026 runtime globals and modules present in the badge's MicroPython
   build. Do not add desktop Python dependencies to badge code.
5. Prefer paletted PNGs, sprite sheets, on-demand loading, and bounded collections.
6. Keep BLE IRQ handlers minimal. Queue received data and process it in `update()`.
7. Never embed credentials. Root `badge/secrets.py` is device configuration, not an app asset.
8. Preserve existing repository behavior and conventions; do not rewrite unrelated apps or launcher code.

## Validate continuously

Run:

```bash
python3 .github/skills/badge-app-builder/scripts/validate_app.py Team1/<app-name>
```

Resolve all errors. Investigate warnings based on the intended target:

- `--target emulator` highlights features the simulator cannot model.
- `--target hardware` checks physical-badge compatibility without emulator-only warnings.
- The default `both` reports both classes of concern.

Validation is advisory for runtime behavior. It does not replace running the emulator and testing real hardware.

## Develop in the emulator

Use the [Pimoroni Badgeware Web Simulator](https://pimoroni.github.io/badgeware-web-simulator/)
for a quick visual preview when it supports the feature being tested. It does
not prove physical-badge behavior.

See [references/emulator.md](references/emulator.md) for controls and setup.
Do not claim BLE, GPIO, true timing, memory pressure, power behavior, or
accessory behavior works merely because the app loads in the simulator.

For a meaningful emulator iteration:

1. Exercise every screen and button path.
2. Test first-run and persisted-state behavior.
3. Re-run the validator after changes.

## Deploy to a physical badge

For persistent deployment, put the badge into USB Disk Mode. The deploy tool
supports both `BADGER/system/apps` and the upstream `TUFTY/apps` layout. For a
transient hardware render test, prefer `mpremote mount badge`. Preview exactly
what will be copied:

```bash
python3 .github/skills/badge-app-builder/scripts/deploy_app.py Team1/<app-name>
```

Then perform the persistent copy:

```bash
python3 .github/skills/badge-app-builder/scripts/deploy_app.py \
  Team1/<app-name> --write
```

If the app already exists, use `--replace`; the tool preserves the previous directory as a timestamped backup. Never deploy `secrets.py` implicitly. Follow [references/physical-badge.md](references/physical-badge.md) for disk mode, safe eject, reset, testing, and recovery.

## Definition of done

State exactly which checks were completed:

- App structure and compatibility validator.
- Emulator paths and controls exercised.
- Screenshot/performance results when relevant.
- Physical badge deployment and on-device checks, if a badge was available.
- Hardware-only features still requiring validation.

Do not describe an app as hardware-compatible if it was tested only in the emulator.
