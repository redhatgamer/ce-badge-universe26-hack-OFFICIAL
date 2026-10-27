"""Offline conference prompts and a locally saved constellation."""

import math

from badgeware import State


STATE_KEY = "team1_side_quest"
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
PHONE_BG = color.rgb(33, 84, 160)
PHONE_LATTICE = color.rgb(43, 98, 176)
STATUS_BG = color.rgb(8, 10, 16)
DOCK_BG = color.rgb(14, 24, 44)
CARD = color.rgb(10, 22, 46)
HEADER_INK = color.rgb(14, 34, 64)
TODO_PEN = color.rgb(150, 180, 220)
HEADER_TOP = (160, 198, 234)
HEADER_BOTTOM = (98, 142, 198)
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
    None,
    ("26", ("GITHUB", "UNIVERSE")),
)
DISC_DAY = 0
DISC_SIZE = 200
DISC_RPM_DEG_PER_MS = 0.015
HIRES_W = 320
HIRES_H = 240
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

STAR_ANIM_MS = 700
INTRO_WIPE_MS = 500
INTRO_SKIP_MS = 700
FINALE_LOCK_MS = 1200
MERGE_AT_MS = 1200
GRID_COLS = 16
GRID_ROWS = 12
LOGICAL_W = 160
LOGICAL_H = 120

state = {"days": [[] for _ in DAY_QUESTS], "day": 0}
selected = 0
star_anim = None
finale_start = None
posters = [None] * len(POSTERS)
disc_img = None
disc_brush = None
disc_shape = None
current_hires = False
phone_bg = None
grid_bg = None
intro_art = None
intro_start = None
intro_done = False
follow_open = False
follow_art = None
screen.font = font.sins


def current_done():
    return state["days"][state["day"]]


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
    if day == DISC_DAY:
        art = image(HIRES_W, HIRES_H)
        art.pen = POSTER_BG
        art.clear()
        posters[day] = art
        return

    glyphs, lines = POSTERS[day]
    art = image(width, height)
    art.pen = POSTER_BG
    art.clear()

    edge = max(2, width // 50)
    cols = 7 * len(glyphs) - 1
    unit = min(width // 13, (height - 4 * edge) // 10)
    glyphs_x = (width - cols * unit) // 2
    glyphs_y = (height - 10 * unit) // 2
    for index, glyph in enumerate(glyphs):
        draw_bitmap(art, BIG_GLYPHS[glyph], glyphs_x + 7 * unit * index, glyphs_y, unit, POSTER_EDGE, edge)
    for index, glyph in enumerate(glyphs):
        draw_bitmap(art, BIG_GLYPHS[glyph], glyphs_x + 7 * unit * index, glyphs_y, unit, None, 0, 10 * unit)

    text_unit = max(1, width // 53)
    ink = max(1, text_unit // 2 + 1)
    gap = text_unit + 1
    text_y = (height - (len(lines) * 7 * text_unit + (len(lines) - 1) * gap)) // 2
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
        "/system/apps/side_quest",
        "/apps/side_quest",
        "/remote/side_quest",
    )
    for folder in folders:
        path = folder + "/assets/" + name
        if folder and file_exists(path):
            return path
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
    draw_text(intro_art, "UNIVERSE", width // 2, height // 2 - 8 * unit, unit, TEXT)
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
            hint_width, _ = screen.measure_text(hint)
            screen.pen = POSTER_BG
            screen.rectangle(0, height - 13 * k, width, 13 * k)
            screen.pen = TEXT
            screen.text(hint, (width - hint_width) / 2, height - 12 * k)

    glow = 0.5 + 0.5 * math.sin(elapsed / 220)
    set_caselights(glow, 1 - glow, 1 - glow, glow)


def init():
    State.load(STATE_KEY, state)
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


def toggle_completion():
    global star_anim, finale_start

    done = current_done()
    if selected in done:
        done.remove(selected)
        star_anim = None
    else:
        done.append(selected)
        star_anim = (selected, badge.ticks)
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


def build_disc():
    # disc.png is an original neon coastal-city design for the finale.
    global disc_img, disc_brush, disc_shape

    path = find_asset("disc.png")
    if not path:
        disc_img = False
        return
    disc_img = image.load(path)
    disc_brush = brush.image(disc_img)
    disc_shape = shape.circle(DISC_SIZE / 2, DISC_SIZE / 2, DISC_SIZE / 2 - 1)


def draw_disc(width, height, since):
    pop = min(1, since / 350)
    scale = 1 - (1 - pop) * (1 - pop) * (1 - pop)
    radius = DISC_SIZE / 2
    cx = width // 2
    cy = height // 2 - 8

    screen.pen = color.rgb(0, 0, 0, 110)
    screen.shape(shape.circle(cx + 4, cy + 6, (radius - 1) * scale))

    disc_shape.transform = (
        mat3().translate(cx, cy).scale(scale).rotate(since * DISC_RPM_DEG_PER_MS).translate(-radius, -radius)
    )
    screen.pen = disc_brush
    screen.shape(disc_shape)

    screen.pen = POSTER_BG
    screen.shape(shape.circle(cx, cy, 12.4 * scale))
    screen.pen = color.rgb(120, 122, 130)
    screen.shape(shape.circle(cx, cy, 12.4 * scale).stroke(1.5))


def prebuild_assets():
    # One asset per frame keeps each hitch short; runs while the intro waits.
    if phone_bg is None:
        build_phone_bg()
    elif grid_bg is None:
        build_grid_bg()
    elif disc_img is None:
        build_disc()
    else:
        for day in range(len(POSTERS)):
            if posters[day] is None:
                build_poster(day)
                return


def draw_finale():
    elapsed = badge.ticks - finale_start
    finale_lights(elapsed)

    if grid_bg is None:
        build_grid_bg()
    day = state["day"]
    if posters[day] is None:
        build_poster(day)
    if day == DISC_DAY and disc_img is None:
        build_disc()

    reveal = min(1, max(0, (elapsed - MERGE_AT_MS) / 300))
    disc_scene = day == DISC_DAY and reveal >= 1 and bool(disc_img)
    set_resolution(disc_scene)
    width = screen.width
    height = screen.height
    k = max(1, width // LOGICAL_W)

    if reveal >= 1:
        screen.blit(posters[day], rect(0, 0, width, height))
        if day != DISC_DAY:
            sweep_x = int((elapsed - MERGE_AT_MS) % 2400 / 2400 * (width + 40)) - 40
            screen.pen = color.rgb(255, 255, 255, 40)
            screen.rectangle(sweep_x, 0, 12 * k, height)
        if disc_scene:
            draw_disc(width, height, elapsed - MERGE_AT_MS - 300)

        if day != DISC_DAY:
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
        hint_width, _ = screen.measure_text(hint)
        screen.pen = POSTER_BG
        screen.rectangle(0, height - 14 * k, width, 14 * k)
        screen.pen = MUTED
        screen.text(hint, (width - hint_width) / 2, height - 9 * k)


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

    phone_bg.pen = DOCK_BG
    phone_bg.rectangle(0, 107 * k, width, height - 107 * k)

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


def draw_status_bar(width, k, done_count):
    screen.pen = TEXT
    for index in range(4):
        bar_h = (2 + index * 2) * k
        screen.rectangle((4 + index * 3) * k, 9 * k - bar_h, 2 * k, bar_h)

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
            screen.pen = color.rgb(255, 255, 255, glow)
            screen.shape(
                shape.rounded_rectangle(x - 2 * k, y - 2 * k, size + 4 * k, size + 4 * k, 7 * k).stroke(2)
            )
        if quest_id in done:
            draw_check(x + size - 2 * k, y + 2 * k, k)
        if star_anim is not None and star_anim[0] == quest_id:
            draw_star_burst(x + size / 2, y + size / 2)


def draw():
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

    screen.pen = HEADER_INK
    heading = "Side Quest"
    heading_width, _ = screen.measure_text(heading)
    screen.text(heading, (width - heading_width) / 2, 12 * k)
    counter = "{}/{}".format(len(done), QUEST_COUNT)
    counter_width, _ = screen.measure_text(counter)
    screen.text(counter, width - counter_width - 5 * k, 12 * k)
    screen.text("UP/DN", 5 * k, 12 * k)

    draw_icons(k, done)

    screen.pen = CARD
    screen.shape(shape.rounded_rectangle(6 * k, 72 * k, width - 12 * k, 34 * k, 4 * k))
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
        if elapsed > INTRO_SKIP_MS and badge.pressed():
            intro_done = True
            intro_art = None
            set_resolution(False)
            set_caselights(0)
        else:
            prebuild_assets()
        return

    if finale_start is not None:
        draw_finale()
        if badge.ticks - finale_start > FINALE_LOCK_MS and badge.pressed():
            finale_start = None
            follow_open = state["day"] == len(DAY_QUESTS) - 1
            set_resolution(follow_open)
            set_caselights(0)
        return

    if follow_open:
        draw_follow()
        if badge.pressed():
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
