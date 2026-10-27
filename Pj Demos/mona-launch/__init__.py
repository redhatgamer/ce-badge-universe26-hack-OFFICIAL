import math
import os
import random
import sys

from badgeware import State

APP_DIR = os.getcwd()
APP_FILE = globals().get("__file__", "")
if "/" in APP_FILE:
    APP_DIR = APP_FILE.rsplit("/", 1)[0] or "/"
    if not APP_DIR.startswith("/"):
        APP_DIR = os.getcwd().rstrip("/") + "/" + APP_DIR

APP_DIRS = (
    APP_DIR,
    "/remote/apps/mona-launch",
    "/system/apps/mona-launch",
    "/apps/mona-launch",
    "/mona-launch",
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

BASE_W = 160
BASE_H = 120
BASE_GROUND_Y = 108
MAX_HEIGHT = 100
FLICK_THRESHOLD_G = 0.5
FLICK_STRENGTH_RANGE_G = 0.8

background = color.rgb(11, 18, 34)
sky = color.rgb(28, 48, 79)
white = color.rgb(246, 248, 252)
muted = color.rgb(158, 177, 201)
green = color.rgb(211, 250, 55)
orange = color.rgb(255, 166, 77)

small_font = font.nope
large_font = font.ziplock
mona_sprites = image.load("mona.png").spritesheet(7, 2)
flying = tuple(mona_sprites.sprite(frame) for frame in range(7))


class MotionInput:
    """Read the badge LSM6DS3 IMU and detect a quick board movement."""

    def __init__(self):
        self.sensor_available = badge is not None and hasattr(badge, "imu")
        self.baseline = None
        self.cooldown_until = 0
        self.reported_error = False

    def read_upward_flick(self):
        if not self.sensor_available:
            return None

        try:
            ax, ay, az, _, _, _ = badge.imu()
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as error:
            self.sensor_available = False
            if not self.reported_error:
                print("Mona Launch IMU unavailable:", error)
                self.reported_error = True
            return None

        acceleration = (ax / 16384, ay / 16384, az / 16384)
        if self.baseline is None:
            self.baseline = acceleration
            return None

        baseline_length = math.sqrt(sum(value * value for value in self.baseline))
        if baseline_length < 0.5:
            self.baseline = acceleration
            return None

        change = tuple(
            new - old
            for old, new in zip(self.baseline, acceleration)
        )
        upward_change = sum(
            delta * gravity / baseline_length
            for delta, gravity in zip(change, self.baseline)
        )
        self.baseline = tuple(
            (old * 0.9) + (new * 0.1)
            for old, new in zip(self.baseline, acceleration)
        )

        if (
            upward_change < FLICK_THRESHOLD_G
            or badge.ticks < self.cooldown_until
        ):
            return None

        self.cooldown_until = badge.ticks + 900
        return min(
            1.0,
            max(
                0.0,
                (upward_change - FLICK_THRESHOLD_G) / FLICK_STRENGTH_RANGE_G,
            ),
        )

    def button_fallback(self):
        if BUTTON_LEFT in badge.pressed() or BUTTON_SELECT in badge.pressed():
            return 0.78
        return None


class Game:
    TITLE = 0
    READY = 1
    FLIGHT = 2
    RESULT = 3

    def __init__(self):
        self.motion = MotionInput()
        self.state = self.TITLE
        self.best_height = 0
        self.height = 0
        self.peak = 0
        self.velocity = 0
        self.started_at = 0
        self.result_at = 0
        self.waiting_for_release = False
        self.new_best = False
        self.trail = []
        self.sparkles = []

    def load(self):
        saved = {"best_height": 0}
        State.load("mona_launch", saved)
        self.best_height = max(0, int(saved.get("best_height", 0)))

    def save(self):
        State.save("mona_launch", {"best_height": int(self.best_height)})

    def start(self, strength):
        self.state = self.FLIGHT
        self.started_at = badge.ticks
        self.height = 0
        self.peak = 0
        self.velocity = 5.5 + (strength * 4.5)
        self.trail = []
        self.sparkles = []

    def enter_ready(self):
        self.state = self.READY
        self.waiting_for_release = True

    def update(self):
        if self.state == self.TITLE:
            self.update_title()
        elif self.state == self.READY:
            self.update_ready()
        elif self.state == self.FLIGHT:
            self.update_flight()
        else:
            self.update_result()

    def update_title(self):
        if BUTTON_LEFT in badge.pressed() or BUTTON_SELECT in badge.pressed():
            self.enter_ready()

    def update_ready(self):
        if self.waiting_for_release:
            if badge.held():
                return
            self.waiting_for_release = False
            self.motion.baseline = None
            return

        strength = self.motion.read_upward_flick()
        if strength is None:
            strength = self.motion.button_fallback()
        if strength is not None:
            self.start(strength)

    def update_flight(self):
        dt = min(badge.ticks_delta, 40) / 16.67
        self.velocity -= 0.105 * dt
        self.height += self.velocity * dt
        self.peak = max(self.peak, self.height)

        if len(self.trail) < 12 or badge.ticks % 2 == 0:
            self.trail.append((badge.ticks, self.height))
        self.trail = self.trail[-12:]

        if random.random() < 0.18:
            self.sparkles.append(
                [random.randint(52, 108), max(10, self.screen_y() - random.randint(4, 18)), badge.ticks]
            )
        self.sparkles = [p for p in self.sparkles if badge.ticks - p[2] < 500]

        if self.height <= 0 and badge.ticks - self.started_at > 350:
            self.height = 0
            self.result_at = badge.ticks
            self.new_best = int(self.peak) > self.best_height
            self.best_height = max(self.best_height, int(self.peak))
            self.save()
            self.state = self.RESULT

    def update_result(self):
        if BUTTON_LEFT in badge.pressed() or BUTTON_SELECT in badge.pressed() or BUTTON_RIGHT in badge.pressed():
            self.enter_ready()

    def screen_y(self):
        return BASE_GROUND_Y - min(MAX_HEIGHT, max(0, int(self.height)))

    def draw(self):
        screen.pen = background
        screen.clear()
        if self.state == self.TITLE:
            self.draw_title()
        elif self.state == self.READY:
            self.draw_ready()
        elif self.state == self.FLIGHT:
            self.draw_flight()
        else:
            self.draw_result()

    def draw_title(self):
        draw_world(0)
        screen.font = large_font
        screen.pen = white
        center("MONA", 20)
        screen.pen = green
        center("LAUNCH", 41)
        draw_mona(80, 83, int(badge.ticks / 140) % 7)
        if int(badge.ticks / 500) % 2:
            screen.font = small_font
            screen.pen = white
            center("SELECT TO BEGIN", 101)

    def draw_ready(self):
        draw_world(0)
        title("READY", 12)
        screen.font = small_font
        screen.pen = white
        center("FLICK UP", 40)
        screen.pen = muted
        center("A TO TEST", 54)
        draw_mona(80, 86, 0)
        draw_score(self.best_height)

    def draw_flight(self):
        draw_world(self.height)
        draw_height_scale(self.peak)
        y = self.screen_y()
        for index, point in enumerate(self.trail):
            trail_y = BASE_GROUND_Y - min(MAX_HEIGHT, max(0, int(point[1])))
            alpha = 30 + (index * 12)
            screen.pen = color.rgb(211, 250, 55, alpha)
            screen.shape(
                shape.circle(
                    layout_x(80),
                    layout_y(trail_y + 10),
                    layout_size(max(1, index // 3 + 1)),
                )
            )
        for x, sparkle_y, created in self.sparkles:
            age = badge.ticks - created
            screen.pen = color.rgb(255, 255, 255, max(0, 180 - age // 3))
            screen.shape(
                shape.circle(layout_x(x), layout_y(sparkle_y), layout_size(1))
            )
        draw_mona(80, y, int(badge.ticks / 100) % 7)
        screen.font = small_font
        screen.pen = white
        screen.text("HEIGHT", layout_x(5), layout_y(4))
        screen.font = large_font
        screen.pen = green
        screen.text(str(int(max(0, self.height))), layout_x(5), layout_y(15))
        screen.font = small_font
        screen.pen = muted
        screen.text("m", layout_x(31), layout_y(21))

    def draw_result(self):
        draw_world(self.peak)
        title("MONA LANDED", 12)
        screen.font = small_font
        screen.pen = muted
        center("Peak height", 39)
        screen.font = large_font
        screen.pen = green
        center(str(int(self.peak)) + " m", 51)
        screen.font = small_font
        screen.pen = orange if self.new_best else white
        center("NEW BEST!" if self.new_best else "Personal best: " + str(self.best_height) + " m", 77)
        screen.pen = muted
        center("Press A, B, or C to launch again", 99)
        draw_mona(80, 89, int(badge.ticks / 140) % 7)


def draw_world(height):
    width = screen.width
    screen_height = screen.height
    ground_y = layout_y(BASE_GROUND_Y)
    progress = min(1.0, max(0.0, height / MAX_HEIGHT))

    for y in range(0, BASE_GROUND_Y, 4):
        altitude = min(
            1.0,
            progress + ((BASE_GROUND_Y - y) / BASE_GROUND_Y) * 0.2,
        )
        screen.pen = color.rgb(*sky_color(altitude))
        screen.shape(
            shape.rectangle(
                0,
                layout_y(y),
                width,
                layout_y(min(BASE_GROUND_Y, y + 4)) - layout_y(y),
            )
        )

    if progress < 0.42:
        cloud_alpha = int(150 * (1.0 - progress / 0.42))
        screen.pen = color.rgb(245, 252, 255, cloud_alpha)
        screen.shape(shape.circle(layout_x(27), layout_y(31), layout_size(8)))
        screen.shape(shape.circle(layout_x(37), layout_y(28), layout_size(11)))
        screen.shape(shape.circle(layout_x(49), layout_y(32), layout_size(7)))
        screen.shape(scaled_rectangle(26, 32, 25, 7))

    if progress > 0.28:
        star_alpha = int(220 * min(1.0, (progress - 0.28) / 0.5))
        screen.pen = color.rgb(255, 255, 255, star_alpha)
        for x, y in ((15, 18), (62, 13), (119, 23), (145, 12), (101, 38), (31, 56)):
            screen.shape(shape.circle(layout_x(x), layout_y(y), layout_size(1)))

    if progress > 0.72:
        planet_alpha = int(210 * min(1.0, (progress - 0.72) / 0.28))
        screen.pen = color.rgb(93, 121, 224, planet_alpha)
        screen.shape(shape.circle(layout_x(128), layout_y(43), layout_size(13)))
        screen.pen = color.rgb(184, 198, 255, planet_alpha // 2)
        screen.shape(shape.circle(layout_x(123), layout_y(39), layout_size(4)))
        screen.shape(shape.circle(layout_x(134), layout_y(47), layout_size(3)))

    ground_alpha = int(255 * max(0.0, 1.0 - (progress / 0.22)))
    if ground_alpha:
        screen.pen = color.rgb(36, 91, 52, ground_alpha)
        screen.shape(shape.rectangle(0, ground_y, width, screen_height - ground_y))
        screen.pen = color.rgb(85, 160, 70, ground_alpha)
        screen.shape(shape.line(0, ground_y, width, ground_y, layout_size(1)))
        for x in range(8, BASE_W, 17):
            screen.shape(
                shape.line(
                    layout_x(x),
                    ground_y,
                    layout_x(x + 3),
                    layout_y(BASE_GROUND_Y - 4),
                    layout_size(1),
                )
            )


def sky_color(progress):
    stops = (
        (0.00, (100, 190, 226)),
        (0.35, (43, 111, 190)),
        (0.68, (17, 34, 91)),
        (1.00, (3, 5, 24)),
    )
    for index in range(1, len(stops)):
        stop, color = stops[index]
        if progress <= stop:
            previous_stop, previous_color = stops[index - 1]
            amount = (progress - previous_stop) / (stop - previous_stop)
            return tuple(
                int(previous_color[channel] + (color[channel] - previous_color[channel]) * amount)
                for channel in range(3)
            )
    return stops[-1][1]


def draw_height_scale(peak):
    ground_y = layout_y(BASE_GROUND_Y)
    screen.pen = color.rgb(255, 255, 255, 100)
    screen.shape(
        shape.line(
            layout_x(137),
            layout_y(8),
            layout_x(137),
            ground_y,
            layout_size(1),
        )
    )
    for height in range(0, 101, 20):
        y = BASE_GROUND_Y - height
        screen.shape(
            shape.line(
                layout_x(134),
                layout_y(y),
                layout_x(140),
                layout_y(y),
                layout_size(1),
            )
        )
        screen.font = small_font
        screen.pen = muted
        screen.text(str(height), layout_x(143), layout_y(y - 4))
    if peak > 0:
        y = BASE_GROUND_Y - min(MAX_HEIGHT, int(peak))
        screen.pen = green
        screen.shape(
            shape.line(
                layout_x(126),
                layout_y(y),
                layout_x(140),
                layout_y(y),
                layout_size(1),
            )
        )


def draw_mona(x, y, frame):
    sprite = flying[frame % len(flying)]
    screen.blit(
        sprite,
        rect(
            layout_x(x - 10),
            layout_y(y - 20),
            layout_x(24),
            layout_y(24),
        ),
    )
    screen.pen = color.rgb(0, 0, 0, 45)
    screen.shape(scaled_rectangle(x - 9, BASE_GROUND_Y - 2, 18, 3))


def draw_score(best):
    screen.font = small_font
    screen.pen = muted
    screen.text("BEST", layout_x(5), layout_y(103))
    screen.pen = green
    screen.text(str(best) + " m", layout_x(31), layout_y(103))


def title(label, y):
    screen.font = large_font
    screen.pen = white
    center(label, y)


def center(label, y):
    width, _ = screen.measure_text(label)
    screen.text(label, (screen.width - width) / 2, layout_y(y))


def layout_x(value):
    return value * screen.width / BASE_W


def layout_y(value):
    return value * screen.height / BASE_H


def layout_size(value):
    scale = min(screen.width / BASE_W, screen.height / BASE_H)
    return max(1, int(round(value * scale)))


def scaled_rectangle(x, y, width, height):
    return shape.rectangle(
        layout_x(x),
        layout_y(y),
        layout_x(width),
        layout_y(height),
    )


game = Game()


def update():
    game.update()
    game.draw()


game.load()


run(update)
