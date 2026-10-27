#!/usr/bin/env python3
"""Create a minimal badge app without overwriting existing work."""

from __future__ import annotations

import argparse
import re
import struct
import sys
import zlib
from pathlib import Path


APP_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
RESERVED_APPS = {"menu", "startup"}
REPO_ROOT = Path(__file__).resolve().parents[4]


def png_chunk(kind: bytes, data: bytes) -> bytes:
    payload = kind + data
    return struct.pack(">I", len(data)) + payload + struct.pack(
        ">I", zlib.crc32(payload) & 0xFFFFFFFF
    )


def make_icon(path: Path) -> None:
    width = height = 24
    background = (211, 250, 55)
    foreground = (13, 17, 23)
    pixels = [[background for _ in range(width)] for _ in range(height)]

    # A small, readable "B" glyph made from 2x2 logical pixels.
    glyph = (
        "11110",
        "10001",
        "10001",
        "11110",
        "10001",
        "10001",
        "11110",
    )
    scale = 2
    x_offset = 7
    y_offset = 5
    for row, line in enumerate(glyph):
        for column, value in enumerate(line):
            if value != "1":
                continue
            for dy in range(scale):
                for dx in range(scale):
                    pixels[y_offset + row * scale + dy][
                        x_offset + column * scale + dx
                    ] = foreground

    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for red, green, blue in row:
            raw.extend((red, green, blue))

    data = b"\x89PNG\r\n\x1a\n"
    data += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    data += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    data += png_chunk(b"IEND", b"")
    path.write_bytes(data)


def app_source(app_name: str, title: str) -> str:
    return f'''"""Generated badge app."""

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
    "/remote/apps/{app_name}",
    "/system/apps/{app_name}",
    "/apps/{app_name}",
    "/{app_name}",
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

screen.font = font.sins


def init():
    pass


def update():
    screen.pen = color.rgb(13, 17, 23)
    screen.rectangle(screen.clip)

    screen.pen = color.rgb(211, 250, 55)
    label = {title!r}
    width, height = screen.measure_text(label)
    screen.text(label, (screen.width - width) / 2, (screen.height - height) / 2)

    if badge.pressed(BUTTON_SELECT):
        print({app_name!r} + ": SELECT pressed")


def on_exit():
    pass


run(update)
'''


def scaffold(app_name: str, title: str, apps_dir: Path) -> Path:
    if not APP_NAME_RE.fullmatch(app_name):
        raise ValueError(
            "App name must start with a lowercase letter or number and contain only "
            "lowercase letters, numbers, hyphens, or underscores."
        )
    if app_name in RESERVED_APPS:
        raise ValueError(f"'{app_name}' is reserved by the badge launcher.")

    app_dir = apps_dir / app_name
    if app_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing app: {app_dir}")

    app_dir.mkdir(parents=True)
    (app_dir / "assets").mkdir()
    (app_dir / "__init__.py").write_text(
        app_source(app_name, title), encoding="utf-8"
    )
    make_icon(app_dir / "icon.png")
    return app_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app_name", help="Directory-safe app name, such as weather-clock")
    parser.add_argument(
        "--title",
        help="Text shown by the starter app (defaults to a title-cased app name)",
    )
    parser.add_argument(
        "--apps-dir",
        type=Path,
        default=REPO_ROOT / "badge" / "apps",
        help="Badge apps directory (default: badge/apps)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    title = args.title or args.app_name.replace("-", " ").replace("_", " ").title()
    try:
        app_dir = scaffold(args.app_name, title, args.apps_dir.resolve())
    except (ValueError, FileExistsError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Created badge app: {app_dir}")
    print(f"Validate: python3 .github/skills/badge-app-builder/scripts/validate_app.py {app_dir}")
    print("Preview: https://pimoroni.github.io/badgeware-web-simulator/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
