"""Offline conference prompts and a locally saved constellation."""

import math

from badgeware import State


STATE_KEY = "team1_vibe_city"
LEGACY_STATE_KEY = "team1_side_quest"
DAY_QUESTS = (
    (
        ("Meet a maker", "Ask someone what", "they're building."),
        ("New territory", "Find a project in", "a new language."),
        ("Trade a tip", "Share one tiny tool", "or workflow tip."),
        ("Imagine it", "Sketch an open-source", "tool you wish existed."),
        ("Origin story", "Ask someone how they", "got into tech."),
        ("Pay it forward", "Share a project you", "think they'll enjoy."),
        ("Listen closely", "Ask what problem", "someone loves solving."),
        ("Three-word pitch", "Describe your next", "idea in three words."),
    ),
    (
        ("Show and tell", "Demo something you", "built to someone."),
        ("Swap stacks", "Compare tools with", "a new friend."),
        ("Ask for help", "Pose a problem you", "are stuck on."),
        ("Contribute", "Find an open issue", "you could help with."),
        ("Hallway mentor", "Share advice you wish", "you'd heard sooner."),
        ("Cross-pollinate", "Chat with someone from", "another field."),
        ("Weekend build", "Describe a tool you'd", "build in a weekend."),
        ("Keep in touch", "Trade handles with a", "new connection."),
    ),
)
QUEST_COUNT = len(DAY_QUESTS[0])

TEXT = color.rgb(245, 243, 229)
MUTED = color.rgb(153, 165, 157)
LIME = color.rgb(211, 250, 55)
PHONE_BG = color.rgb(16, 4, 30)
PHONE_LATTICE = color.rgb(40, 14, 68)
STATUS_BG = color.rgb(8, 2, 16)
DOCK_BG = color.rgb(10, 2, 20)
CARD = color.rgb(36, 5, 58)
HEADER_INK = color.rgb(36, 5, 58)
HEADER_TEXT = color.rgb(255, 236, 255)
TODO_PEN = color.rgb(214, 160, 240)
NEON_PINK = color.rgb(255, 82, 170)
NEON_CYAN = color.rgb(64, 220, 230)
HEADER_TOP = (132, 36, 168)
HEADER_BOTTOM = (72, 12, 112)
ICON_COLORS = (
    color.rgb(238, 126, 62),
    color.rgb(82, 190, 92),
    color.rgb(236, 152, 52),
    color.rgb(128, 72, 202),
    color.rgb(156, 98, 52),
    color.rgb(112, 118, 130),
    color.rgb(222, 178, 64),
    color.rgb(64, 150, 226),
)
# 12x12 glyphs in phone-app order: mail, chat, tasks, cloud, contacts, settings, camera, globe.
ICON_GLYPHS = (
    ("111111111111", "111000000111", "101100001101", "100110011001", "100011110001", "100001100001",
     "100000000001", "100000000001", "100000000001", "100000000001", "100000000001", "111111111111"),
    ("000000000000", "011111111110", "111111111111", "111111111111", "111011011011", "111111111111",
     "111111111111", "011111111110", "001111111100", "000110000000", "000100000000", "000000000000"),
    ("111111111111", "100000000001", "101011111101", "100000000001", "101011111101", "100000000001",
     "101011111101", "100000000001", "101011111101", "100000000001", "100000000001", "111111111111"),
    ("000000000000", "000011110000", "001111111100", "011110011110", "111100001111", "111110011111",
     "111110011111", "011111111110", "001111111100", "000000000000", "000000000000", "000000000000"),
    ("111111111111", "111111111111", "111110011111", "111100001111", "111100001111", "111110011111",
     "111000000111", "110000000011", "110000000011", "111111111111", "111111111111", "000000000000"),
    ("000011110000", "001111111100", "011111111110", "111110011111", "111100001111", "111000000111",
     "111000000111", "111100001111", "111110011111", "011111111110", "001111111100", "000011110000"),
    ("000000000000", "000111100000", "111111111111", "111100001111", "111100001111", "111000000111",
     "111001100111", "111000000111", "111100001111", "111111111111", "111111111111", "000000000000"),
    ("000011110000", "001110011100", "011110011110", "111110011111", "111110011111", "100000000001",
     "111110011111", "111110011111", "011110011110", "001110011100", "000011110000", "000000000000"),
)
GRID_BG = color.rgb(16, 4, 30)
GRID_EMPTY = color.rgb(34, 12, 58)
GTA_RGB = ((52, 98, 214), (150, 72, 200), (255, 82, 170), (240, 150, 72))
GREEN_RGB = ((14, 68, 41), (0, 109, 50), (38, 166, 65), (57, 211, 83))
POSTER_BG = color.rgb(16, 4, 30)
POSTER_EDGE = color.rgb(72, 6, 104)
POSTER_INK = color.rgb(36, 5, 58)
POSTER_PINK = color.rgb(255, 82, 170)
SUNSET_STOPS = (
    (0.0, (52, 98, 214)),
    (0.5, (255, 82, 170)),
    (1.0, (232, 148, 70)),
)
OUTLINE_OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1))
BIG_GLYPHS = {
    "2": ("111111", "111111", "000011", "000011", "111111", "111111", "110000", "110000", "111111", "111111"),
    "6": ("111111", "111111", "110000", "110000", "111111", "111111", "110011", "110011", "111111", "111111"),
}
# Per day: big gradient glyphs, then stacked title lines.
POSTERS = (
    ("", ("DAY ONE", "COMPLETED")),
    ("26", ("GITHUB", "UNIVERSE")),
)
PIXEL_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "01010", "01010", "00100"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}

try:
    PREV_BUTTON = BUTTON_LEFT
    NEXT_BUTTON = BUTTON_RIGHT
    LOG_BUTTON = BUTTON_SELECT
except NameError:
    # The web simulator only defines the older A/B/C buttons.
    PREV_BUTTON = BUTTON_A
    NEXT_BUTTON = BUTTON_C
    LOG_BUTTON = BUTTON_B
SKIP_BUTTONS = (PREV_BUTTON, NEXT_BUTTON, LOG_BUTTON, BUTTON_UP, BUTTON_DOWN)

STAR_ANIM_MS = 700
STREAK_MILESTONES = (3, 5, 8, 12, 16)
STREAK_FLASH_MS = 1400
FLAME_ROWS = ("00100", "01100", "01110", "11111", "11111", "11111", "01110")
FLAME_OUTER = color.rgb(255, 128, 32)
FLAME_CORE = color.rgb(255, 224, 96)
INTRO_WIPE_MS = 500
INTRO_SKIP_MS = 700
FINALE_LOCK_MS = 1200
MERGE_AT_MS = 1200
GRID_COLS = 16
GRID_ROWS = 12
LOGICAL_W = 160
LOGICAL_H = 120

state = {"days": [[] for _ in DAY_QUESTS], "day": 0, "streak": 0}
selected = 0
star_anim = None
streak_flash = None
finale_start = None
posters = [None] * len(POSTERS)
current_hires = False
phone_bg = None
grid_bg = None
mona_sheet = None
MONA_DAY = 0
MONA_COLS = 8
MONA_ROWS = 6
MONA_COUNT = MONA_COLS * MONA_ROWS
MONA_W = 72
MONA_H = 64
MONA_TOP = 2
MONA_SHOW = 0.85
CAPTION_Y = 62
HINT_H = 14
MONA_TURN_MS = 3000
intro_art = None
intro_start = None
intro_done = False
follow_open = False
follow_art = None
screen.font = font.sins


def current_done():
    return state["days"][state["day"]]


def any_pressed():
    for button in SKIP_BUTTONS:
        if badge.pressed(button):
            return True
    return False


def green(level, alpha=255):
    r, g, b = GREEN_RGB[level]
    return color.rgb(r, g, b, alpha)


def gta(level, alpha=255):
    r, g, b = GTA_RGB[level]
    return color.rgb(r, g, b, alpha)


def make_levels(count):
    levels = []
    seed = 4242
    for _ in range(count):
        seed = (seed * 75 + 74) % 65537
        levels.append(seed % 4)
    return levels


LEVELS = make_levels(GRID_COLS * GRID_ROWS)


def sunset(t):
    for index in range(1, len(SUNSET_STOPS)):
        t1, c1 = SUNSET_STOPS[index]
        if t <= t1:
            t0, c0 = SUNSET_STOPS[index - 1]
            f = (t - t0) / (t1 - t0)
            return color.rgb(*[int(c0[i] + (c1[i] - c0[i]) * f) for i in range(3)])
    return color.rgb(*SUNSET_STOPS[-1][1])


def bitmap_runs(bitmap):
    runs = []
    for row_index, row in enumerate(bitmap):
        col = 0
        while col < len(row):
            if row[col] != "1":
                col += 1
                continue
            start = col
            while col < len(row) and row[col] == "1":
                col += 1
            runs.append((row_index, start, col - start))
    return runs


def draw_bitmap(target, bitmap, x, y, unit, pen, grow=0, gradient_height=None):
    runs = bitmap_runs(bitmap)
    offsets = OUTLINE_OFFSETS if grow else ((0, 0),)
    for dx, dy in offsets:
        for row_index, start, length in runs:
            run_x = int(x + start * unit + dx * grow)
            run_y = int(y + row_index * unit + dy * grow)
            if gradient_height is None:
                target.pen = pen
                target.rectangle(run_x, run_y, length * unit, unit)
                continue
            for slice_y in range(0, unit, 2):
                target.pen = sunset((row_index * unit + slice_y) / gradient_height)
                target.rectangle(run_x, run_y + slice_y, length * unit, min(2, unit - slice_y))


def draw_text(target, text, center_x, y, unit, pen, grow=0, gradient=False):
    draw_x = center_x - (len(text) * 6 - 1) * unit / 2
    for index, character in enumerate(text):
        draw_bitmap(
            target, PIXEL_FONT[character], draw_x + index * 6 * unit, y, unit, pen, grow,
            7 * unit if gradient else None,
        )


def build_poster(day):
    width = LOGICAL_W
    height = LOGICAL_H
    glyphs, lines = POSTERS[day]
    art = image(width, height)
    art.pen = POSTER_BG
    art.clear()

    text_unit = max(1, width // 53)
    ink = max(1, text_unit // 2 + 1)
    gap = text_unit + 1

    if not glyphs:
        # Caption under the spinning head: a big first line, a smaller second.
        y = CAPTION_Y
        for line_index, line in enumerate(lines):
            unit = text_unit if line_index == 0 else max(1, text_unit - 1)
            line_ink = max(1, unit // 2 + 1)
            draw_text(art, line, width // 2, y, unit, POSTER_PINK, line_ink + 1)
            draw_text(art, line, width // 2, y, unit, POSTER_INK, line_ink)
            draw_text(art, line, width // 2, y, unit, TEXT)
            y += 7 * unit + gap + 1
        posters[day] = art
        return

    edge = max(2, width // 50)
    area = height - HINT_H - 1
    cols = 7 * len(glyphs) - 1
    unit = min(width // 13, (area - 4 * edge) // 10)
    glyphs_x = (width - cols * unit) // 2
    glyphs_y = (area - 10 * unit) // 2
    for index, glyph in enumerate(glyphs):
        draw_bitmap(art, BIG_GLYPHS[glyph], glyphs_x + 7 * unit * index, glyphs_y, unit, POSTER_EDGE, edge)
    for index, glyph in enumerate(glyphs):
        draw_bitmap(art, BIG_GLYPHS[glyph], glyphs_x + 7 * unit * index, glyphs_y, unit, None, 0, 10 * unit)

    text_y = (area - (len(lines) * 7 * text_unit + (len(lines) - 1) * gap)) // 2
    for line_index, line in enumerate(lines):
        y = text_y + line_index * (7 * text_unit + gap)
        draw_text(art, line, width // 2, y, text_unit, POSTER_PINK, ink + 1)
        draw_text(art, line, width // 2, y, text_unit, POSTER_INK, ink)
        draw_text(art, line, width // 2, y, text_unit, TEXT)
    posters[day] = art


def set_resolution(hires):
    # The art screens are 320x240; the interface and animations are drawn at 160x120.
    global current_hires

    if hires == current_hires:
        return
    current_hires = hires
    try:
        badge.mode((HIRES if hires else LORES) | VSYNC)
    except NameError:
        pass


def find_asset(name):
    here = globals().get("__file__", "")
    folders = (
        here.rsplit("/", 1)[0] if "/" in here else "",
        "/system/apps/vibe_city",
        "/apps/vibe_city",
        "/remote/vibe_city",
    )
    for folder in folders:
        path = folder + "/assets/" + name
        if folder and file_exists(path):
            return path
    # The web simulator keeps uploaded assets next to __init__.py at its root.
    if file_exists("/" + name):
        return "/" + name
    return None


def build_intro():
    global intro_art

    # welcome.png was rendered offline from the Damion font (SIL OFL).
    path = find_asset("welcome.png")
    if path:
        intro_art = image.load(path)
        return

    width = screen.width
    height = screen.height
    unit = max(1, width // 53)
    intro_art = image(width, height)
    intro_art.pen = POSTER_BG
    intro_art.clear()
    draw_text(intro_art, "VIBE", width // 2, height // 2 - 8 * unit, unit, TEXT)
    draw_text(intro_art, "CITY", width // 2, height // 2 + 2 * unit, unit, TEXT)


def draw_intro():
    width = screen.width
    height = screen.height
    elapsed = badge.ticks - intro_start

    screen.blit(intro_art, rect(0, 0, width, height))

    cover = int(height / 2 * (1 - min(1, elapsed / INTRO_WIPE_MS)))
    if cover > 0:
        screen.pen = POSTER_BG
        screen.rectangle(0, 0, width, cover)
        screen.rectangle(0, height - cover, width, cover)
    else:
        sweep_x = int((elapsed - INTRO_WIPE_MS) % 1600 / 1600 * (width + 40)) - 40
        screen.pen = color.rgb(255, 255, 255, 40)
        screen.rectangle(sweep_x, 0, 12, height)

        if (elapsed - INTRO_WIPE_MS) // 500 % 2 == 0:
            k = max(1, width // 160)
            hint = "PRESS ANY BUTTON"
            hint_width, hint_height = screen.measure_text(hint)
            hint_y = height - hint_height - 4 * k
            screen.pen = POSTER_BG
            screen.rectangle(0, hint_y - k, width, height - hint_y + k)
            screen.pen = TEXT
            screen.text(hint, (width - hint_width) / 2, hint_y)

    glow = 0.5 + 0.5 * math.sin(elapsed / 220)
    set_caselights(glow, 1 - glow, 1 - glow, glow)


def init():
    State.load(STATE_KEY, state)
    if not any(state["days"]) and state["streak"] == 0:
        # Carry over progress saved under the old Side Quest name.
        State.load(LEGACY_STATE_KEY, state)
    days = state.get("days")
    if not isinstance(days, list) or len(days) != len(DAY_QUESTS):
        days = [[] for _ in DAY_QUESTS]
    state["days"] = [
        [
            quest_id
            for quest_id in done
            if isinstance(quest_id, int) and 0 <= quest_id < QUEST_COUNT
        ]
        if isinstance(done, list)
        else []
        for done in days
    ]
    if state.get("day") not in range(len(DAY_QUESTS)):
        state["day"] = 0
    streak = state.get("streak")
    state["streak"] = streak if isinstance(streak, int) and streak > 0 else 0


def toggle_completion():
    global star_anim, finale_start, streak_flash

    done = current_done()
    if selected in done:
        done.remove(selected)
        star_anim = None
        state["streak"] = 0
        streak_flash = None
    else:
        done.append(selected)
        star_anim = (selected, badge.ticks)
        state["streak"] += 1
        if state["streak"] in STREAK_MILESTONES:
            streak_flash = badge.ticks
        if len(done) == QUEST_COUNT:
            finale_start = badge.ticks
    State.save(STATE_KEY, state)


def switch_day():
    global selected, star_anim

    state["day"] = (state["day"] + 1) % len(DAY_QUESTS)
    selected = 0
    star_anim = None
    State.save(STATE_KEY, state)


def draw_star_burst(x, y):
    global star_anim

    elapsed = badge.ticks - star_anim[1]
    if elapsed >= STAR_ANIM_MS:
        star_anim = None
        return

    t = elapsed / STAR_ANIM_MS
    fade = int(255 * (1 - t))

    half = 3 + 3 * math.sin(t * math.pi)
    screen.pen = green(min(3, int(t * 4)))
    screen.shape(shape.rounded_rectangle(x - half, y - half, half * 2, half * 2, 1))

    reach = 4 + t * 10
    screen.pen = green(3, fade)
    screen.shape(shape.rounded_rectangle(x - reach, y - reach, reach * 2, reach * 2, 2).stroke(1))

    for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        distance = 4 + t * 10
        screen.rectangle(int(x + dx * distance) - 1, int(y + dy * distance) - 1, 2, 2)

    screen.text("+1", int(x) - 5, int(y - 8 - t * 14))


def set_caselights(*levels):
    # The web simulator has no case lights.
    if hasattr(badge, "caselights"):
        badge.caselights(*levels)


def finale_lights(elapsed):
    if elapsed < MERGE_AT_MS:
        lit = (elapsed // 150) % 4
        set_caselights(*[1.0 if index == lit else 0.08 for index in range(4)])
        return
    beat = math.sin((elapsed - MERGE_AT_MS) / 220)
    high = 0.55 + 0.45 * beat
    low = 0.55 - 0.45 * beat
    set_caselights(high, low, low, high)


def build_grid_bg():
    global grid_bg

    width = LOGICAL_W
    height = LOGICAL_H
    cell = width / GRID_COLS
    size = int(cell) - 2
    grid_bg = image(width, height)
    grid_bg.pen = GRID_BG
    grid_bg.clear()
    grid_bg.pen = GRID_EMPTY
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            grid_bg.rectangle(int(col * cell) + 1, int(row * cell) + 1, size, size)


def draw_grid(width, elapsed):
    cell = width / GRID_COLS
    size = int(cell) - 2
    screen.blit(grid_bg, vec2(0, 0))
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            lit_for = elapsed - (col + row) * 35
            if lit_for > 0:
                level = (LEVELS[row * GRID_COLS + col] + int(elapsed / 200)) % 4
                screen.pen = gta(level, min(255, int(lit_for * 2)))
                screen.rectangle(int(col * cell) + 1, int(row * cell) + 1, size, size)


def prebuild_assets():
    # One asset per frame keeps each hitch short; runs while the intro waits.
    if phone_bg is None:
        build_phone_bg()
    elif grid_bg is None:
        build_grid_bg()
    elif mona_sheet is None:
        build_mona()
    else:
        for day in range(len(POSTERS)):
            if posters[day] is None:
                build_poster(day)
                return


def build_mona():
    global mona_sheet

    path = find_asset("mona_turn.png")
    mona_sheet = image.load(path).spritesheet(MONA_COLS, MONA_ROWS) if path else False


def draw_mona(width, height, since):
    k = max(1, width // LOGICAL_W)
    pop = min(1, since / 350)
    scale = 1 - (1 - pop) * (1 - pop) * (1 - pop)
    frame = int(since % MONA_TURN_MS * MONA_COUNT / MONA_TURN_MS) % MONA_COUNT
    bob = math.sin(since / 450) * 2 * k
    show = MONA_SHOW * k
    cx = width / 2
    cy = MONA_TOP * k + MONA_H * show / 2 + bob

    pulse = 0.5 + 0.5 * math.sin(since / 500)
    for index, radius in enumerate((33, 27, 21)):
        screen.pen = color.rgb(255, 110, 200, 22 + index * 8 + int(pulse * 10))
        screen.shape(shape.circle(cx, cy, (radius + pulse * 3) * show * scale))

    w = MONA_W * show * scale
    h = MONA_H * show * scale
    screen.blit(mona_sheet.sprite(frame % MONA_COLS, frame // MONA_COLS), rect(cx - w / 2, cy - h / 2, w, h))


def draw_finale():
    elapsed = badge.ticks - finale_start
    finale_lights(elapsed)

    if grid_bg is None:
        build_grid_bg()
    day = state["day"]
    if posters[day] is None:
        build_poster(day)
    if day == MONA_DAY and mona_sheet is None:
        build_mona()
    reveal = min(1, max(0, (elapsed - MERGE_AT_MS) / 300))
    set_resolution(False)
    width = screen.width
    height = screen.height
    k = max(1, width // LOGICAL_W)

    if reveal >= 1:
        screen.blit(posters[day], rect(0, 0, width, height))
        sweep_x = int((elapsed - MERGE_AT_MS) % 2400 / 2400 * (width + 40)) - 40
        screen.pen = color.rgb(255, 255, 255, 40)
        screen.rectangle(sweep_x, 0, 12 * k, height)

        if day == MONA_DAY:
            if mona_sheet:
                draw_mona(width, height, elapsed - MERGE_AT_MS - 300)
        else:
            footer = "DAY {} SHIPPED".format(state["day"] + 1)
            footer_width, _ = screen.measure_text(footer)
            screen.pen = TEXT
            screen.text(footer, (width - footer_width) / 2, height - 9)
    else:
        draw_grid(width, elapsed)
        if reveal > 0:
            band = int(height * reveal)
            screen.pen = POSTER_BG
            screen.rectangle(0, (height - band) // 2, width, band)

    if elapsed > FINALE_LOCK_MS + 800:
        hint = "PRESS ANY BUTTON"
        hint_width, hint_height = screen.measure_text(hint)
        hint_y = height - hint_height - 4 * k
        screen.pen = POSTER_BG
        screen.rectangle(0, min(hint_y - k, height - HINT_H * k), width, height)
        screen.pen = MUTED
        screen.text(hint, (width - hint_width) / 2, hint_y)


def build_phone_bg():
    global phone_bg

    width = LOGICAL_W
    height = LOGICAL_H
    k = max(1, width // 160)
    phone_bg = image(width, height)
    phone_bg.pen = PHONE_BG
    phone_bg.clear()

    phone_bg.pen = PHONE_LATTICE
    for x in range(-height, width, 20 * k):
        phone_bg.line(x, 0, x + height, height)
        phone_bg.line(x, height, x + height, 0)

    phone_bg.pen = STATUS_BG
    phone_bg.rectangle(0, 0, width, 11 * k)

    header_h = 11 * k
    for row in range(header_h):
        t = row / header_h
        phone_bg.pen = color.rgb(
            *[int(HEADER_TOP[i] + (HEADER_BOTTOM[i] - HEADER_TOP[i]) * t) for i in range(3)]
        )
        phone_bg.rectangle(0, 11 * k + row, width, 1)

    phone_bg.pen = NEON_PINK
    phone_bg.rectangle(0, 22 * k, width, k)
    phone_bg.pen = NEON_CYAN
    phone_bg.rectangle(0, 23 * k, width, k)

    phone_bg.pen = DOCK_BG
    phone_bg.rectangle(0, 107 * k, width, height - 107 * k)
    phone_bg.pen = NEON_PINK
    phone_bg.rectangle(0, 107 * k, width, k)

    for quest_id in range(QUEST_COUNT):
        paint_icon(phone_bg, quest_id, k)


def icon_pos(quest_id, k):
    return (10 + 40 * (quest_id % 4)) * k, (25 + 24 * (quest_id // 4)) * k


def paint_icon(target, quest_id, k):
    x, y = icon_pos(quest_id, k)
    size = 20 * k
    target.pen = ICON_COLORS[quest_id]
    target.shape(shape.rounded_rectangle(x, y, size, size, 5 * k))
    target.pen = color.rgb(255, 255, 255, 45)
    target.shape(shape.rounded_rectangle(x + k, y + k, size - 2 * k, size // 2 - k, 4 * k))
    target.pen = TEXT
    for row, start, length in ICON_RUNS[quest_id]:
        target.rectangle(x + (4 + start) * k, y + (4 + row) * k, length * k, k)


def draw_check(cx, cy, k):
    screen.pen = LIME
    screen.shape(shape.circle(cx, cy, 4 * k))
    screen.pen = HEADER_INK
    screen.line(cx - 2 * k, cy, cx - k, cy + 2 * k)
    screen.line(cx - k, cy + 2 * k, cx + 2 * k, cy - 2 * k)


def draw_flame(x, y, k):
    for row, cells in enumerate(FLAME_ROWS):
        for col, cell in enumerate(cells):
            if cell == "1":
                core = row >= 4 and 1 <= col <= 3
                screen.pen = FLAME_CORE if core else FLAME_OUTER
                screen.rectangle(x + col * k, y + row * k, k, k)


def draw_status_bar(width, k, done_count):
    screen.pen = TEXT
    for index in range(4):
        bar_h = (2 + index * 2) * k
        screen.rectangle((4 + index * 3) * k, 9 * k - bar_h, 2 * k, bar_h)

    if state["streak"] > 0:
        draw_flame(19 * k, 2 * k, k)
        screen.pen = TEXT
        screen.text(str(state["streak"]), 26 * k, 0)

    label = "DAY {}".format(state["day"] + 1)
    label_width, _ = screen.measure_text(label)
    screen.text(label, (width - label_width) / 2, 0)

    battery_x = width - 21 * k
    screen.shape(shape.rounded_rectangle(battery_x, 2 * k, 14 * k, 6 * k, k).stroke(1))
    screen.rectangle(battery_x + 14 * k, 4 * k, 2 * k, 2 * k)
    screen.pen = LIME
    screen.rectangle(battery_x + k, 3 * k, (12 * k * done_count) // QUEST_COUNT, 4 * k)


ICON_RUNS = tuple(bitmap_runs(glyph) for glyph in ICON_GLYPHS)


def draw_icons(k, done):
    size = 20 * k
    for quest_id in range(QUEST_COUNT):
        x, y = icon_pos(quest_id, k)

        if quest_id == selected:
            glow = int(190 + 65 * math.sin(badge.ticks / 180))
            screen.pen = color.rgb(255, 82, 170, glow)
            screen.shape(
                shape.rounded_rectangle(x - 2 * k, y - 2 * k, size + 4 * k, size + 4 * k, 7 * k).stroke(2)
            )
        if quest_id in done:
            draw_check(x + size - 2 * k, y + 2 * k, k)
        if star_anim is not None and star_anim[0] == quest_id:
            draw_star_burst(x + size / 2, y + size / 2)


def draw():
    global streak_flash

    width = screen.width
    height = screen.height
    k = max(1, width // 160)
    title, prompt_line_1, prompt_line_2 = DAY_QUESTS[state["day"]][selected]
    done = current_done()
    completed = selected in done

    if phone_bg is None:
        build_phone_bg()
    screen.blit(phone_bg, vec2(0, 0))

    draw_status_bar(width, k, len(done))

    heading = "Vibe City"
    if streak_flash is not None:
        flash_elapsed = badge.ticks - streak_flash
        if flash_elapsed < STREAK_FLASH_MS:
            heading = "{} STREAK!".format(state["streak"])
            pulse = 0.5 + 0.5 * math.sin(flash_elapsed / 90)
            set_caselights(pulse, 1 - pulse, 1 - pulse, pulse)
        else:
            streak_flash = None
            set_caselights(0)

    screen.pen = HEADER_TEXT
    heading_width, heading_height = screen.measure_text(heading)
    header_y = 11 * k + (11 * k - heading_height) // 2
    screen.text(heading, (width - heading_width) // 2, header_y)
    counter = "{}/{}".format(len(done), QUEST_COUNT)
    counter_width, _ = screen.measure_text(counter)
    screen.text(counter, width - counter_width - 5 * k, header_y)
    screen.text("UP/DN", 5 * k, header_y)

    draw_icons(k, done)

    screen.pen = CARD
    screen.shape(shape.rounded_rectangle(6 * k, 72 * k, width - 12 * k, 34 * k, 4 * k))
    screen.pen = NEON_PINK
    screen.shape(shape.rounded_rectangle(6 * k, 72 * k, width - 12 * k, 34 * k, 4 * k).stroke(1))
    screen.pen = LIME
    screen.text(title, 10 * k, 73 * k)
    badge_text = "DONE" if completed else "TO DO"
    badge_width, _ = screen.measure_text(badge_text)
    screen.pen = LIME if completed else TODO_PEN
    screen.text(badge_text, width - badge_width - 10 * k, 73 * k)
    screen.pen = TEXT
    screen.text(prompt_line_1, 10 * k, 83 * k)
    screen.text(prompt_line_2, 10 * k, 93 * k)

    screen.pen = TEXT
    mid_y = 113 * k
    screen.line(16 * k, mid_y - 3 * k, 12 * k, mid_y)
    screen.line(12 * k, mid_y, 16 * k, mid_y + 3 * k)
    screen.line(width - 16 * k, mid_y - 3 * k, width - 12 * k, mid_y)
    screen.line(width - 12 * k, mid_y, width - 16 * k, mid_y + 3 * k)
    action = "SELECT UNDO" if completed else "SELECT LOG"
    action_width, _ = screen.measure_text(action)
    screen.text(action, (width - action_width) / 2, 108 * k)


def draw_follow():
    global follow_art

    if follow_art is None:
        path = find_asset("follow.png")
        follow_art = image.load(path) if path else False
    if follow_art:
        screen.blit(follow_art, rect(0, 0, screen.width, screen.height))
        return
    screen.pen = POSTER_BG
    screen.clear()
    screen.pen = TEXT
    screen.text("FOLLOW ME ON GITHUB", 10, 40)
    screen.text("github.com/redhatgamer", 10, 60)


def on_exit():
    set_caselights(0)


def update():
    global selected, finale_start, intro_art, intro_start, intro_done, follow_open, follow_art

    if not intro_done:
        if intro_art is None:
            build_intro()
            set_resolution(True)
            intro_start = badge.ticks
        draw_intro()
        elapsed = badge.ticks - intro_start
        if elapsed > INTRO_SKIP_MS and any_pressed():
            intro_done = True
            intro_art = None
            set_resolution(False)
            set_caselights(0)
        else:
            prebuild_assets()
        return

    if finale_start is not None:
        draw_finale()
        if badge.ticks - finale_start > FINALE_LOCK_MS and any_pressed():
            finale_start = None
            follow_open = state["day"] == len(DAY_QUESTS) - 1
            set_resolution(follow_open)
            set_caselights(0)
        return

    if follow_open:
        draw_follow()
        if any_pressed():
            follow_open = False
            follow_art = None
            set_resolution(False)
        return

    if badge.pressed(PREV_BUTTON):
        selected = (selected - 1) % QUEST_COUNT
    elif badge.pressed(NEXT_BUTTON):
        selected = (selected + 1) % QUEST_COUNT

    if badge.pressed(BUTTON_UP) or badge.pressed(BUTTON_DOWN):
        switch_day()
    elif badge.pressed(LOG_BUTTON):
        toggle_completion()

    draw()


init()
run(update)
