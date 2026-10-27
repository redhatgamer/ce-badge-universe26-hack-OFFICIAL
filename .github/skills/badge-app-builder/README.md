# Badge App Builder skill

Project-local GitHub Copilot skill for creating and maintaining apps for the
Hackable Conference Badge.

## Use it for

- Turning an app or game idea into a working `TeamN/<name>` CE submission.
- Choosing controls and UI that fit the 160x120 logical display.
- Reusing the Universe 2026 `badge` runtime, Wi-Fi, BLE, IR, state, LED, and
  battery patterns from the
  current apps.
- Scaffolding and validating an app.
- Iterating with the [Pimoroni Badgeware Web Simulator](https://pimoroni.github.io/badgeware-web-simulator/)
  for a quick browser check.
- Safely copying one app to a physical badge in USB Disk Mode.

The skill treats the physical RP2350B badge as the compatibility target. It
explicitly identifies behavior that the web simulator cannot prove.
Universe 2025 Badgeware examples are archived upstream under `badge25/` and
must not be used as the active API for new apps.

## Bundled tools

```bash
# Create an app
python3 .github/skills/badge-app-builder/scripts/scaffold_app.py my-app \
  --title "My App" --apps-dir Team1

# Check emulator and hardware compatibility
python3 .github/skills/badge-app-builder/scripts/validate_app.py Team1/my-app

# Check every submission in the team folder
python3 .github/skills/badge-app-builder/scripts/validate_submissions.py Team1

# Preview, then perform, a physical badge deployment
python3 .github/skills/badge-app-builder/scripts/deploy_app.py Team1/my-app
python3 .github/skills/badge-app-builder/scripts/deploy_app.py \
  Team1/my-app --write
```

The generated app uses one small directory lookup that supports the web/native
simulator, temporary remote mounts, `BADGER/system/apps`, and `TUFTY/apps`.
The validator rejects desktop-only `os.path` calls before they reach a badge.

The deploy command is dry-run by default, detects either supported USB layout,
validates for hardware first, copies only the selected app, excludes
credentials and generated files, and requires `--replace` before replacing an
installed app.

## Knowledge sources

Stable constraints and recipes are bundled under `references/`. For APIs that
are advanced, missing, or likely to have changed, the skill consults the
first-party `badger/home` and `badger/pimoroni-pico` repositories rather than
guessing.
