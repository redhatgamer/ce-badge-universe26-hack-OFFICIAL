# Universe 2026 physical badge workflow

For the authoritative connection and serial workflow, read
`badger/home/hardware/USB_SERIAL.md`.

## Persistent deployment

1. Connect the badge with a data-capable USB-C cable.
2. Enter USB mass-storage mode and wait for the `BADGER` or `TUFTY` volume.
3. Confirm it contains `system/apps` or `apps`.
4. Preview deployment with the repository deploy script.
5. Write only after reviewing the file list.
6. Safely eject, press RESET once, and launch the app.

```bash
python3 .github/skills/badge-app-builder/scripts/deploy_app.py badge/apps/my_app
python3 .github/skills/badge-app-builder/scripts/deploy_app.py badge/apps/my_app --write
```

Use `--replace` only when replacing an existing app. The tool keeps a backup
outside the installed apps directory and never copies credentials, caches, or
bytecode.

## Transient hardware testing

Use `mpremote mount badge` for a temporary render or API test. The normal
serial REPL mounts `/system` read-only on the tested firmware, so a direct
serial copy is not a replacement for USB mass-storage deployment.

## On-device checks

Test startup, every logical control, HOME cleanup, saved state, missing or
malformed state, network failure, BLE discovery and disconnect, touch,
orientation, IMU behavior, IR range, LEDs, battery, and charging as applicable.

Do not claim hardware compatibility from an emulator run or a transient mount
alone. Firmware recovery and `.uf2` flashing must use the intended 2026 release
and hardware revision.
