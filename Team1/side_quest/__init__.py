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

BACKGROUND = color.rgb(18, 23, 24)
PANEL = color.rgb(34, 43, 40)
TEXT = color.rgb(245, 243, 229)
MUTED = color.rgb(153, 165, 157)
LIME = color.rgb(211, 250, 55)
CORAL = color.rgb(255, 126, 99)
GH_BG = color.rgb(13, 17, 23)
GH_EMPTY = color.rgb(22, 27, 34)
MERGE_PURPLE = color.rgb(137, 87, 229)
GREEN_RGB = ((14, 68, 41), (0, 109, 50), (38, 166, 65), (57, 211, 83))

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
FINALE_LOCK_MS = 1200
MERGE_AT_MS = 1200
GRID_COLS = 16
GRID_ROWS = 12

state = {"days": [[] for _ in DAY_QUESTS], "day": 0}
selected = 0
star_anim = None
finale_start = None
screen.font = font.sins


def current_done():
    return state["days"][state["day"]]


def green(level, alpha=255):
    r, g, b = GREEN_RGB[level]
    return color.rgb(r, g, b, alpha)


def make_levels(count):
    levels = []
    seed = 4242
    for _ in range(count):
        seed = (seed * 75 + 74) % 65537
        levels.append(seed % 4)
    return levels


LEVELS = make_levels(GRID_COLS * GRID_ROWS)


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


def draw_finale():
    width = screen.width
    height = screen.height
    elapsed = badge.ticks - finale_start
    cell = width / GRID_COLS
    size = int(cell) - 2

    screen.pen = GH_BG
    screen.clear()

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x = int(col * cell) + 1
            y = int(row * cell) + 1
            screen.pen = GH_EMPTY
            screen.rectangle(x, y, size, size)
            lit_for = elapsed - (col + row) * 35
            if lit_for > 0:
                level = (LEVELS[row * GRID_COLS + col] + int(elapsed / 200)) % 4
                screen.pen = green(level, min(255, int(lit_for * 2)))
                screen.rectangle(x, y, size, size)

    merge_t = min(1, max(0, (elapsed - MERGE_AT_MS) / 250))
    if merge_t > 0:
        cx = width / 2
        panel_w = width * 0.7
        full_h = height * 0.4
        panel_h = full_h * merge_t
        top = height * 0.45 - full_h / 2
        panel_y = height * 0.45 - panel_h / 2

        screen.pen = GH_BG
        screen.shape(shape.rounded_rectangle((width - panel_w) / 2, panel_y, panel_w, panel_h, 4))
        screen.pen = MERGE_PURPLE
        screen.shape(
            shape.rounded_rectangle((width - panel_w) / 2, panel_y, panel_w, panel_h, 4).stroke(2)
        )

        if merge_t == 1:
            label = "MERGED"
            label_width, _ = screen.measure_text(label)
            screen.pen = MERGE_PURPLE
            screen.shape(
                shape.rounded_rectangle(cx - label_width / 2 - 6, top + 6, label_width + 12, 14, 7)
            )
            screen.pen = TEXT
            screen.text(label, cx - label_width / 2, int(top + 9))

            for line, offset, pen in (
                ("DAY {} SHIPPED".format(state["day"] + 1), 26, green(3)),
                ("TO MAIN", 37, MUTED),
            ):
                line_width, _ = screen.measure_text(line)
                screen.pen = pen
                screen.text(line, cx - line_width / 2, int(top + offset))

    if elapsed > FINALE_LOCK_MS + 800:
        hint = "PRESS ANY BUTTON"
        hint_width, _ = screen.measure_text(hint)
        screen.pen = GH_BG
        screen.rectangle(0, height - 14, width, 14)
        screen.pen = MUTED
        screen.text(hint, (width - hint_width) / 2, height - 9)


def draw_progress():
    width = screen.width
    height = screen.height
    start_x = 12
    end_x = width - 12
    y = int(height * 0.86)
    step = (end_x - start_x) / (QUEST_COUNT - 1)

    screen.pen = MUTED
    screen.line(start_x, y, end_x, y)
    for quest_id in range(QUEST_COUNT):
        x = start_x + step * quest_id
        animating = star_anim is not None and star_anim[0] == quest_id
        screen.pen = LIME if quest_id in current_done() else PANEL
        screen.shape(shape.circle(x, y, 3))
        if quest_id == selected:
            screen.pen = CORAL
            screen.shape(shape.circle(x, y, 4).stroke(1))
        if animating:
            draw_star_burst(x, y)


def draw():
    width = screen.width
    height = screen.height
    title, prompt_line_1, prompt_line_2 = DAY_QUESTS[state["day"]][selected]
    completed = selected in current_done()

    screen.pen = BACKGROUND
    screen.clear()

    screen.pen = TEXT
    screen.text("SIDE QUEST", 7, 5)
    counter = "DAY {}  {:02d}/{:02d}".format(state["day"] + 1, selected + 1, QUEST_COUNT)
    counter_width, _ = screen.measure_text(counter)
    screen.text(counter, width - counter_width - 7, 5)

    screen.pen = PANEL
    screen.line(7, int(height * 0.17), width - 7, int(height * 0.17))

    screen.pen = LIME
    screen.text(title, 8, int(height * 0.23))
    screen.pen = TEXT
    screen.text(prompt_line_1, 8, int(height * 0.37))
    screen.text(prompt_line_2, 8, int(height * 0.48))

    screen.pen = PANEL
    screen.shape(shape.rounded_rectangle(6, int(height * 0.62), width - 12, 16, 3))
    screen.pen = LIME if completed else CORAL
    screen.shape(shape.circle(14, int(height * 0.62) + 8, 2))
    screen.pen = TEXT
    status = "IN YOUR CONSTELLATION" if completed else "READY WHEN YOU ARE"
    screen.text(status, 21, int(height * 0.62) + 4)

    screen.pen = MUTED
    stars = "{} / {} STARS".format(len(current_done()), QUEST_COUNT)
    screen.text(stars, 7, int(height * 0.75))
    day_hint = "UP/DOWN: DAY"
    day_hint_width, _ = screen.measure_text(day_hint)
    screen.text(day_hint, width - day_hint_width - 7, int(height * 0.75))
    draw_progress()

    screen.pen = TEXT
    screen.text("LEFT/RIGHT", 7, height - 9)
    action = "SELECT UNDO" if completed else "SELECT LOG"
    action_width, _ = screen.measure_text(action)
    screen.text(action, width - action_width - 7, height - 9)


def update():
    global selected, finale_start

    if finale_start is not None:
        draw_finale()
        if badge.ticks - finale_start > FINALE_LOCK_MS and badge.pressed():
            finale_start = None
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
