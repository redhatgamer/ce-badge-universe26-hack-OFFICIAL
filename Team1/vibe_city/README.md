# Vibe City

An offline conference game for the GitHub Universe 2026 badge. Each day has
eight social quests (meet a maker, trade a tip, ...). Log them as you
complete them, build a streak, and unlock a celebration when you finish a day.
It needs no Wi-Fi or accounts, and progress is saved on the badge.

## Features

- **Two days of quests.** Eight prompts per day, shown as phone-style app icons.
- **Quest log.** Check a quest off (or undo it) with one button.
- **Progress meter.** A "battery" in the status bar fills as you finish quests,
  and a counter shows `done/8`.
- **Streak.** A flame and number in the status bar count the quests you have
  logged in a row. Undoing a quest resets it to 0. Reaching 3, 5, 8, 12 and 16
  flashes `N STREAK!` in the header and pulses the case LEDs.
- **Day-complete finale.** Logging the eighth quest of a day plays an animated
  grid, a poster reveal and an LED light show. Day 1 shows a spinning Mona;
  Day 2 shows the "26 GITHUB UNIVERSE" poster.
- **Follow screen.** Dismissing the Day 2 finale opens a "follow me on GitHub"
  image.
- **Animated intro.** A "Welcome to Vibe City" splash with a blinking
  "PRESS ANY BUTTON" prompt.
- **Saved progress.** Quests, current day and streak survive HOME, RESET and
  power-off.

## Controls

| Action | Badge | Web simulator |
| --- | --- | --- |
| Previous quest | LEFT | A |
| Next quest | RIGHT | C |
| Log / undo selected quest | SELECT | B |
| Switch Day 1 / Day 2 | UP or DOWN | - |
| Skip intro, dismiss finale or follow screen | Any button | Any button |

The simulator only defines the older A/B/C buttons, so the app falls back to
them there. HOME belongs to the launcher and is not used by the app.

## How it flows

1. **Intro** plays in 320x240. Any button skips it after 0.7 s. Assets for the
   rest of the app are built in the background during the intro so the UI opens
   without hitches.
2. **Quest list** is drawn at 160x120. Move with LEFT/RIGHT, log with SELECT,
   switch days with UP/DOWN.
3. **Finale** starts when all eight quests of a day are checked. It locks input
   for 1.2 s, then any button returns to the list.
4. **Follow screen** opens after the Day 2 finale only. Any button closes it.

## What is saved and what is not

Saved under the state key `team1_vibe_city` every time you log, undo or switch
day. Progress saved under the earlier name (`team1_side_quest`) is loaded once
if no Vibe City progress exists yet:

- The checked quests for each day.
- The day you were last on.
- The current streak.

Reset each time the app opens: the intro replays, the highlighted quest returns
to the first one, and finales and the follow screen are not replayed. Loaded
state is validated, so a missing or corrupt value falls back to a safe default.

## Function reference

All code is in [`__init__.py`](./__init__.py).

### State and quest logic

| Function | Purpose |
| --- | --- |
| `init()` | Loads saved state, drops invalid quest IDs, and validates the day and streak. |
| `current_done()` | Returns the list of completed quest IDs for the current day. |
| `toggle_completion()` | Logs or undoes the selected quest, updates the streak and milestone flash, starts the finale on the eighth quest, and saves. |
| `switch_day()` | Switches between Day 1 and Day 2, resets the selection and saves. |

### Main loop

| Function | Purpose |
| --- | --- |
| `update()` | Called every frame. Routes to the intro, finale, follow screen or quest list and handles input. |
| `draw()` | Draws the quest list: status bar, header, icons, quest card and the SELECT hint. |
| `on_exit()` | Turns the case LEDs off when the app closes. |

### Quest list drawing

| Function | Purpose |
| --- | --- |
| `build_phone_bg()` | Pre-renders the phone-style background, header gradient and dock. |
| `draw_status_bar(width, k, done_count)` | Draws signal bars, the streak flame and number, the DAY label and the progress battery. |
| `draw_flame(x, y, k)` | Draws the pixel-art streak flame. |
| `draw_icons(k, done)` | Draws the eight quest icons with selection glow, check marks and the +1 burst. |
| `icon_pos(quest_id, k)` | Returns the pixel position of a quest icon. |
| `paint_icon(target, quest_id, k)` | Paints one icon into an image. |
| `draw_check(cx, cy, k)` | Draws the completed check mark. |
| `draw_star_burst(x, y)` | Animates the "+1" burst when a quest is logged. |

### Intro, finale and follow screen

| Function | Purpose |
| --- | --- |
| `build_intro()` | Loads `welcome.png`, or draws a text fallback if it is missing. |
| `draw_intro()` | Draws the wipe, light sweep, blinking "PRESS ANY BUTTON" hint and LED glow. |
| `draw_finale()` | Draws the animated grid, poster reveal, Mona, footer and hint. |
| `build_grid_bg()` / `draw_grid(width, elapsed)` | Pre-render and animate the finale pixel grid. |
| `build_poster(day)` | Renders the poster image for a day. |
| `build_mona()` / `draw_mona(width, height, since)` | Load and animate the spinning Mona from the sprite sheet. |
| `finale_lights(elapsed)` | Drives the case LEDs during the finale. |
| `draw_follow()` | Draws the "follow me on GitHub" image, with a text fallback. |
| `prebuild_assets()` | Builds one asset per frame while the intro runs to avoid stutter. |

### Helpers

| Function | Purpose |
| --- | --- |
| `set_resolution(hires)` | Switches between 320x240 (art screens) and 160x120 (UI). |
| `set_caselights(*levels)` | Sets the case LEDs, and does nothing in the simulator. |
| `find_asset(name)` | Locates a file in the app's `assets/` folder on the badge or host. |
| `draw_bitmap`, `draw_text`, `bitmap_runs` | Draw the built-in pixel font and large glyphs, with optional outline or sunset gradient. |
| `sunset(t)`, `green(level, alpha)`, `gta(level, alpha)`, `make_levels(count)` | Colour gradients and the grid's pseudo-random brightness levels. |

## Assets

In [`assets/`](./assets):

- `welcome.png` - intro splash (rendered from the Damion font, SIL OFL).
- `mona_turn.png` - 8x6 sprite sheet for the spinning Mona.
- `follow.png` - final "follow me" screen.

Every asset has a fallback, so the app still runs if one is missing.

## Customising

- **Quests:** edit `DAY_QUESTS` (title, then two prompt lines). Each day must
  have the same number of quests.
- **Streak milestones:** edit `STREAK_MILESTONES`.
- **Day posters:** edit `POSTERS`.

## Checks and deployment

```bash
python3 .github/skills/badge-app-builder/scripts/validate_app.py Team1/vibe_city
python3 .github/skills/badge-app-builder/scripts/deploy_app.py Team1/vibe_city \
  --mount /Volumes/BADGER --replace --write
```

Put the badge in USB disk mode first (open the Mass Storage app), eject the
volume safely after copying, and press RESET once.

Hardware-only behaviour (case LEDs, real timing, touch input) can't be proven
in the simulator, so test it on a physical badge. Check the intro, the streak
flame and milestone flash, both finales, and that progress survives a reset.
